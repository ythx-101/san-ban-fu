#!/usr/bin/env python3
"""
三板斧 (San Ban Fu) - Claude 写，Codex 审，循环改

双 AI 交叉验证的代码生成工具：
1. Claude 快速生成原型
2. Codex 独立审核
3. Claude 根据审核修复
4. 重复 N 轮，输出生产级代码

用法:
    python3 san_ban_fu.py "议题" --rounds 3 --dir ./output
"""

import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

# CLI 配置
CLAUDE_CMD = "claude"  # Claude Code CLI
CODEX_CMD = "codex"    # Codex CLI

# 支持的代码文件扩展名
CODE_EXTENSIONS = {
    ".py", ".ts", ".js", ".tsx", ".jsx",  # 脚本
    ".go", ".rs", ".java", ".kt", ".swift",  # 编译型
    ".rb", ".php", ".pl", ".lua",  # 其他脚本
    ".c", ".cpp", ".h", ".hpp",  # C/C++
    ".sh", ".bash", ".zsh",  # Shell
    ".sol",  # Solidity
}


def log(msg: str, level: str = "INFO"):
    """打印日志"""
    icons = {"INFO": "📝", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "STEP": "🔄"}
    print(f"{icons.get(level, '📝')} [{datetime.now().strftime('%H:%M:%S')}] {msg}")


def call_claude(prompt: str, cwd: Path, max_turns: int = 30) -> str:
    """通过 Claude Code CLI 调用 Claude"""
    cmd = [CLAUDE_CMD, "-p", "--max-turns", str(max_turns)]

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=300
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Claude 执行超时")
    except FileNotFoundError:
        raise RuntimeError("Claude Code CLI 未安装，请先安装: https://claude.ai/code")

    if result.returncode != 0:
        raise RuntimeError(f"Claude 失败: {result.stderr[:200]}")

    return result.stdout


def call_codex(cwd: Path, focus: str = "") -> Optional[str]:
    """调用 Codex 审核，失败返回 None"""
    prompt = f"Review this codebase for bugs, security issues, and improvements. {focus}".strip()
    cmd = [CODEX_CMD, "review", prompt]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=180
        )
    except subprocess.TimeoutExpired:
        log("Codex 审核超时", "ERR")
        return None
    except FileNotFoundError:
        log("Codex 未安装，请先安装: https://openai.com/codex", "ERR")
        return None

    # 检查退出码
    if result.returncode != 0:
        if "not inside a trusted" in result.stderr.lower():
            log("Codex 需要在 git repo 中运行，请先 git init", "WARN")
        else:
            log(f"Codex 失败 (exit {result.returncode}): {result.stderr[:200]}", "ERR")
        return None

    output = result.stdout + result.stderr

    # 提取 codex 总结部分
    lines = output.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('codex'):
            return '\n'.join(lines[i:])

    return output[-3000:] if len(output) > 3000 else output


def get_files_snapshot(cwd: Path) -> dict:
    """获取目录中所有文件的快照（路径 -> mtime）"""
    return {str(f.relative_to(cwd)): f.stat().st_mtime for f in cwd.rglob("*") if f.is_file()}


def find_code_files(cwd: Path) -> list:
    """查找所有代码文件"""
    code_files = []
    for f in cwd.rglob("*"):
        if f.is_file() and f.suffix.lower() in CODE_EXTENSIONS:
            code_files.append(f)
    return code_files


def phase_generate(topic: str, cwd: Path) -> bool:
    """阶段1: 生成原型"""
    log(f"生成原型: {topic}", "STEP")

    before = get_files_snapshot(cwd)

    prompt = f"""你是一个快速原型开发者。请根据以下议题生成代码：

**议题**: {topic}

**工作目录**: {cwd}

**要求**:
1. 生成完整可运行的代码
2. 代码简洁，有必要注释
3. 包含 README.md 说明用法
4. 包含 requirements.txt（如果是 Python）

直接用 Write 工具把文件写到 {cwd}/"""

    try:
        call_claude(prompt, cwd)
    except RuntimeError as e:
        log(str(e), "ERR")
        return False

    after = get_files_snapshot(cwd)
    new_files = set(after.keys()) - set(before.keys())
    modified_files = {f for f in before if f in after and after[f] != before[f]}
    deleted_files = set(before.keys()) - set(after.keys())

    if deleted_files:
        log(f"警告：删除了 {len(deleted_files)} 个文件", "WARN")
        for f in sorted(deleted_files)[:3]:
            log(f"  - {f}", "WARN")

    if new_files or modified_files:
        if new_files:
            log(f"生成了 {len(new_files)} 个新文件", "OK")
            for f in sorted(new_files)[:5]:
                log(f"  + {f}", "INFO")
            if len(new_files) > 5:
                log(f"  ... 还有 {len(new_files) - 5} 个文件", "INFO")
        if modified_files:
            log(f"修改了 {len(modified_files)} 个文件", "OK")
            for f in sorted(modified_files)[:3]:
                log(f"  ~ {f}", "INFO")
        return True
    else:
        log("未生成或修改文件", "ERR")
        return False


def phase_review(cwd: Path, round_num: int) -> Optional[str]:
    """阶段2: Codex 审核"""
    log(f"Codex 审核（第{round_num}轮）", "STEP")

    focus = "Focus on security, concurrency, error handling, and edge cases."
    review = call_codex(cwd, focus)

    if review is None:
        return None

    p1_count = review.lower().count("[p1]")
    p2_count = review.lower().count("[p2]")

    log(f"发现 {p1_count} 个 P1, {p2_count} 个 P2 问题", "INFO")

    return review


def phase_fix(cwd: Path, review: str, round_num: int) -> bool:
    """阶段3: 根据审核修复"""
    log(f"修复问题（第{round_num}轮）", "STEP")

    code_files = find_code_files(cwd)
    if not code_files:
        log("没有找到代码文件，跳过修复", "WARN")
        return True

    log(f"找到 {len(code_files)} 个代码文件", "INFO")

    before = get_files_snapshot(cwd)

    prompt = f"""Codex 审核发现以下问题：

{review}

请根据审核意见修复代码。工作目录: {cwd}

只修复被指出的问题，不要做额外的改动。"""

    try:
        call_claude(prompt, cwd, max_turns=20)
    except RuntimeError as e:
        log(f"修复失败: {e}", "ERR")
        return False

    after = get_files_snapshot(cwd)
    modified = {f for f in before if f in after and after[f] != before[f]}
    new_files = set(after.keys()) - set(before.keys())

    if modified or new_files:
        log(f"修复完成（修改 {len(modified)} 个，新增 {len(new_files)} 个）", "OK")
        return True
    else:
        log("Claude 未修改任何文件", "WARN")
        return True


def generate_report(topic: str, cwd: Path, rounds: int, reviews: list) -> Path:
    """生成审核报告"""
    report_path = cwd / "REVIEW_REPORT.md"

    report = f"""# 三板斧审核报告

## 议题
{topic}

## 审核轮数
{rounds}

## 审核历史

"""
    for i, review in enumerate(reviews, 1):
        if review:
            report += f"### 第 {i} 轮\n\n```\n{review[:1500]}...\n```\n\n"
        else:
            report += f"### 第 {i} 轮\n\n*审核失败或跳过*\n\n"

    report += """## 生成文件

"""
    for f in sorted(cwd.iterdir()):
        if f.is_file():
            report += f"- `{f.name}` ({f.stat().st_size} bytes)\n"

    report += f"""
## 生成时间
{datetime.now().isoformat()}

## 状态
已完成 {rounds} 轮审核修复

---
*Generated by [三板斧](https://github.com/anthropics/san-ban-fu)*
"""

    report_path.write_text(report)
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="三板斧 - Claude 写，Codex 审，循环改",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 san_ban_fu.py "JWT 认证中间件"
  python3 san_ban_fu.py "WebSocket 服务器" --rounds 5
  python3 san_ban_fu.py "修复认证 bug" --dir ./src --clean
        """
    )
    parser.add_argument("topic", help="议题/需求描述")
    parser.add_argument("--rounds", type=int, default=3, help="审核轮数（默认3）")
    parser.add_argument("--dir", type=str, default="./san-ban-fu-output", help="输出目录")
    parser.add_argument("--clean", action="store_true", help="清空输出目录后再开始")

    args = parser.parse_args()

    cwd = Path(args.dir).resolve()

    # 安全检查：清空目录
    if args.clean and cwd.exists():
        import shutil
        dangerous_paths = {
            Path.home(),
            Path.home() / "Desktop",
            Path.home() / "Documents",
            Path.home() / "Downloads",
            Path("/"),
            Path(".").resolve(),
            Path("..").resolve(),
        }
        if cwd in dangerous_paths or len(cwd.parts) <= 2:
            log(f"拒绝清空危险路径: {cwd}", "ERR")
            return 1
        shutil.rmtree(cwd)
        log(f"已清空: {cwd}", "INFO")

    cwd.mkdir(parents=True, exist_ok=True)

    print()
    print("  ╔═══════════════════════════════════════╗")
    print("  ║         三板斧 (San Ban Fu)           ║")
    print("  ║   Claude 写 · Codex 审 · 循环改       ║")
    print("  ╚═══════════════════════════════════════╝")
    print()

    log(f"议题: {args.topic}", "INFO")
    log(f"目录: {cwd}", "INFO")
    log(f"轮数: {args.rounds}", "INFO")
    print()

    # 阶段1: 生成原型
    if not phase_generate(args.topic, cwd):
        log("原型生成失败", "ERR")
        return 1

    # 阶段2-3: 审核 + 修复循环
    reviews = []
    successful_reviews = 0
    for round_num in range(1, args.rounds + 1):
        print()
        log(f"===== 第 {round_num}/{args.rounds} 轮 =====", "STEP")

        review = phase_review(cwd, round_num)
        reviews.append(review)

        if review is None:
            log("Codex 审核失败，跳过本轮修复", "WARN")
            continue

        successful_reviews += 1

        if "no issues" in review.lower() or "no actionable" in review.lower():
            log("Codex 未发现问题，提前结束", "OK")
            break

        if not phase_fix(cwd, review, round_num):
            log("修复失败，终止循环", "ERR")
            break

    if successful_reviews == 0:
        log("所有 Codex 审核均失败", "ERR")
        return 1

    # 生成报告
    print()
    report_path = generate_report(args.topic, cwd, len(reviews), reviews)
    log(f"审核报告: {report_path}", "OK")

    print()
    log("=" * 50, "INFO")
    log("三板斧完成!", "OK")
    log(f"输出目录: {cwd}", "INFO")
    log(f"审核轮数: {len(reviews)}", "INFO")

    print()
    for f in sorted(cwd.iterdir()):
        if f.is_file():
            print(f"  📄 {f.name}")

    return 0


if __name__ == "__main__":
    exit(main())
