# 三板斧 (San Ban Fu)

**Claude 写，Codex 审，循环改** — 双 AI 交叉验证的代码生成工具

```
议题 → Claude 生成 → Codex 审核 → Claude 修复 → (重复 N 轮) → 生产级代码
```

## 为什么需要这个？

单个 AI 写代码容易有盲区。三板斧让两个不同的 AI 系统互相配合：
- **Claude** (Anthropic) 负责快速生成和修复
- **Codex** (OpenAI) 负责独立审查，找 bug/安全漏洞/边界问题

不是自己审自己，是真正的交叉验证。

## 安装

### 前置条件

你需要同时拥有：
- [Claude Code](https://claude.ai/code) 订阅 — `claude` CLI 可用
- [Codex](https://openai.com/codex) 订阅 — `codex` CLI 可用

```bash
# 验证安装
claude --version
codex --version
```

### 安装三板斧

```bash
# 克隆仓库
git clone https://github.com/anthropics/san-ban-fu.git
cd san-ban-fu

# 或者直接下载脚本
curl -O https://raw.githubusercontent.com/anthropics/san-ban-fu/main/san_ban_fu.py
chmod +x san_ban_fu.py
```

### 作为 Claude Code Skill 安装

```bash
# 复制到 skills 目录
mkdir -p ~/.claude/skills/san-ban-fu
cp SKILL.md ~/.claude/skills/san-ban-fu/
cp san_ban_fu.py ~/.claude/skills/san-ban-fu/
```

然后在 Claude Code 中使用 `/san-ban-fu "你的议题"`

## 用法

### 命令行

```bash
# 基本用法（默认 3 轮审核）
python3 san_ban_fu.py "实现一个 JWT 认证中间件"

# 指定轮数
python3 san_ban_fu.py "WebSocket 聊天服务器" --rounds 5

# 指定输出目录
python3 san_ban_fu.py "REST API with rate limiting" --dir ./my-api

# 清空目录后重新开始
python3 san_ban_fu.py "fix the auth bug" --dir ./existing-project --clean
```

### 作为 Skill

```
/san-ban-fu "OAuth2 登录流程"
/san-ban-fu "并发安全的缓存实现" --rounds 5
```

## 工作流程

```
第 1 轮
├── Claude 生成原型代码
├── Codex 审核 → 发现 2 个 P1, 3 个 P2
└── Claude 修复所有问题

第 2 轮
├── Codex 再次审核 → 发现 1 个 P2
└── Claude 修复

第 3 轮
├── Codex 审核 → "No actionable issues"
└── 提前结束

输出
├── 你的代码文件
└── REVIEW_REPORT.md（审核历史）
```

## 输出示例

```
📝 [14:32:01] Proto 启动
📝 [14:32:01] 议题: JWT 认证中间件
📝 [14:32:01] 目录: /Users/you/jwt-middleware
📝 [14:32:01] 轮数: 3

🔄 [14:32:01] 生成原型: JWT 认证中间件
✅ [14:32:15] 生成了 4 个新文件
📝 [14:32:15]   + auth.py
📝 [14:32:15]   + middleware.py
📝 [14:32:15]   + README.md
📝 [14:32:15]   + requirements.txt

🔄 [14:32:15] ===== 第 1/3 轮 =====
🔄 [14:32:15] Codex 审核（第1轮）
📝 [14:32:28] 发现 1 个 P1, 2 个 P2 问题
🔄 [14:32:28] 修复问题（第1轮）
✅ [14:32:41] 修复完成（修改 2 个，新增 0 个）

🔄 [14:32:41] ===== 第 2/3 轮 =====
🔄 [14:32:41] Codex 审核（第2轮）
📝 [14:32:52] 发现 0 个 P1, 1 个 P2 问题
🔄 [14:32:52] 修复问题（第2轮）
✅ [14:33:02] 修复完成（修改 1 个，新增 0 个）

🔄 [14:33:02] ===== 第 3/3 轮 =====
🔄 [14:33:02] Codex 审核（第3轮）
✅ [14:33:12] Codex 未发现问题，提前结束

✅ [14:33:12] 审核报告: /Users/you/jwt-middleware/REVIEW_REPORT.md
📝 [14:33:12] ==================================================
✅ [14:33:12] Proto 完成!

  📄 auth.py
  📄 middleware.py
  📄 README.md
  📄 REVIEW_REPORT.md
  📄 requirements.txt
```

## 支持的语言

Python, TypeScript, JavaScript, Go, Rust, Java, Kotlin, Swift, Ruby, PHP, C/C++, Shell, Solidity 等 20+ 种语言。

## License

MIT
