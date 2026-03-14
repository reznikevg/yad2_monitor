#!/bin/bash
cd "$(dirname "$0")"
if [ -d .venv ]; then
  .venv/bin/python main.py "$@"
else
  python3 main.py "$@"
fi
