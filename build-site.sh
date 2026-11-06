#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 tools/build.py
python3 tools/validate.py
