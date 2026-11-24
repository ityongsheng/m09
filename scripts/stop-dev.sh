#!/bin/sh
set -eu
port=${M09_PORT:-8080}
pids=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
if [ -z "$pids" ]; then
  echo "m09 未发现监听端口 $port 的开发服务"
  exit 0
fi
echo "$pids" | xargs kill -TERM
echo "已请求停止 m09 开发服务：$pids"
