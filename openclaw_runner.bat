@echo off
set OPENCLAW_CONFIG_PATH=E:\TEST_SYNC\10_projekte_dashboard\10.1_aktiv\openclaw-main\MyClaw\openclaw-main\openclaw.json
cd /d E:\TEST_SYNC\10_projekte_dashboard\10.1_aktiv\openclaw-main\MyClaw\openclaw-main
"C:\Program Files\nodejs\node.exe" openclaw.mjs agent --local --agent main -m "%OPENCLAW_PROMPT%"
