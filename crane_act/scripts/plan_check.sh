#!/bin/bash
# plan-only check of each line of a UTF-8 command file with D's commander (read-only use)
cd ${D_LLM:-$HOME/pai_final/d_llm}
while IFS= read -r c; do [ -n "$c" ] && python3 commander.py --plan-only --log /tmp/plan_check.jsonl "$c" | grep -E "指令|判定|応答|^  [0-9]"; done < "$1"
