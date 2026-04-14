---
name: san-ban-fu
description: 三板斧 - Claude 写，Codex 审，循环改。双 AI 交叉验证的代码生成工具。
allowed-tools: Bash
---

# 三板斧 (San Ban Fu)

Claude 写，Codex 审，循环改 — 双 AI 交叉验证的代码生成工具。

## 用法

```
/san-ban-fu <议题>
/san-ban-fu <议题> --rounds N      # 指定审核轮数（默认3）
/san-ban-fu <议题> --dir <path>    # 指定输出目录
/san-ban-fu <议题> --clean         # 清空目录后开始
```

## 示例

```
/san-ban-fu "JWT 认证中间件"
/san-ban-fu "WebSocket 聊天服务器" --rounds 5
/san-ban-fu "OAuth2 登录流程" --dir ./auth-service
```

## 流程

```
1. Claude 生成原型代码
2. Codex 独立审核（找 bug/安全/并发问题）
3. Claude 根据审核修复
4. 重复 2-3 共 N 轮
5. 输出最终代码 + REVIEW_REPORT.md
```

## 前置条件

- Claude Code 订阅 (`claude` CLI)
- Codex 订阅 (`codex` CLI)

## 执行

```bash
_ARGS="$ARGUMENTS"
_SCRIPT_DIR="$(dirname "$0")"

# 解析参数
_TOPIC=""
_ROUNDS="3"
_DIR=""
_CLEAN=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --rounds) _ROUNDS="$2"; shift 2 ;;
    --dir) _DIR="$2"; shift 2 ;;
    --clean) _CLEAN="--clean"; shift ;;
    *) _TOPIC="$1"; shift ;;
  esac
done

# 从 ARGUMENTS 解析
if [ -z "$_TOPIC" ]; then
  _TOPIC=$(echo "$_ARGS" | sed -E 's/--rounds [0-9]+//g; s/--dir [^ ]+//g; s/--clean//g' | xargs)
fi

if echo "$_ARGS" | grep -q '\-\-rounds'; then
  _ROUNDS=$(echo "$_ARGS" | grep -oP '(?<=--rounds )\d+')
fi

if echo "$_ARGS" | grep -q '\-\-dir'; then
  _DIR=$(echo "$_ARGS" | grep -oP '(?<=--dir )[^ ]+')
fi

if echo "$_ARGS" | grep -q '\-\-clean'; then
  _CLEAN="--clean"
fi

if [ -z "$_TOPIC" ]; then
  echo "用法: /san-ban-fu <议题> [--rounds N] [--dir path] [--clean]"
  exit 1
fi

# 构建命令
_CMD="python3 ${_SCRIPT_DIR}/san_ban_fu.py \"$_TOPIC\" --rounds $_ROUNDS"
[ -n "$_DIR" ] && _CMD="$_CMD --dir $_DIR"
[ -n "$_CLEAN" ] && _CMD="$_CMD $_CLEAN"

echo "🪓 三板斧启动..."
echo "📝 议题: $_TOPIC"
echo "🔄 轮数: $_ROUNDS"
echo ""

eval $_CMD
```
