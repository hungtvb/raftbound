#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo 'Publishing RAFTBOUND A08 to https://github.com/hungtvb/raftbound'
git status --short
git push -u origin main
