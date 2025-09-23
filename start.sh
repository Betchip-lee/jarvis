#!/usr/bin/env bash
set -e
python JARVIS_QAI_PRO.py &
sleep 1
python jarvis_dash.py &
sleep 1
python telegram_bot.py &
echo "Jarvis Kitchen Sink started."
wait -n
