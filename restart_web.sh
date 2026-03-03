#!/usr/bin/env bash
set -euo pipefail

PORT=8080
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_MODE=0
LOG_FILE="${ROOT_DIR}/.cursor/web-server.log"

for arg in "$@"; do
  case "${arg}" in
    --daemon)
      DAEMON_MODE=1
      ;;
    *)
      echo "Unknown argument: ${arg}" >&2
      echo "Usage: ./restart_web.sh [--daemon]" >&2
      exit 1
      ;;
  esac
done

if command -v lsof >/dev/null 2>&1; then
  pids="$(lsof -ti:${PORT} || true)"
  if [ -n "${pids}" ]; then
    # Graceful stop first, then force-kill if needed.
    echo "${pids}" | xargs kill 2>/dev/null || true
    for _ in {1..20}; do
      sleep 0.1
      if ! lsof -ti:${PORT} >/dev/null 2>&1; then
        break
      fi
    done
    if lsof -ti:${PORT} >/dev/null 2>&1; then
      lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    fi
  fi
fi

cd "${ROOT_DIR}"

if [ "${DAEMON_MODE}" -eq 1 ]; then
  mkdir -p "$(dirname "${LOG_FILE}")"
  nohup python3 -m importer.web --no-open >"${LOG_FILE}" 2>&1 &
  new_pid=$!
  for _ in {1..60}; do
    if lsof -ti:${PORT} >/dev/null 2>&1; then
      echo "Web server started in daemon mode (pid=${new_pid}, port=${PORT})"
      echo "Logs: ${LOG_FILE}"
      exit 0
    fi
    sleep 0.25
  done
  echo "Timed out waiting for web server on port ${PORT}" >&2
  echo "Check logs: ${LOG_FILE}" >&2
  exit 1
fi

python3 -m importer.web --no-open
