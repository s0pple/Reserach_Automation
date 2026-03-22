@echo off
echo ==========================================
echo Starte isolierte Gemini-CLI Sandbox
echo ==========================================
echo.
echo Diese Umgebung ist temporär (--rm) und läuft
echo als Nicht-Root-Benutzer (-u 1000:1000).
echo Sie kann den Code in /app lesen/schreiben,
echo aber nicht den Host beschädigen.
echo.

REM Pfade auf dem Windows-Host
set PROJECT_DIR=%CD%
set CLI_DIR=C:\Users\olive\Downloads\gemini-cli-main\gemini-cli-main

REM Wähle ein Image, das zu der CLI passt (hier ubuntu, ggf. auf python/node anpassen)
REM Wir fügen "--network host" hinzu, falls die CLI auf unseren Proxy Port 9001 zugreifen muss!
docker run -it --rm ^
  --name gemini_safe_sandbox ^
  -v "%PROJECT_DIR%:/app" ^
  -v "%CLI_DIR%:/gemini-cli" ^
  -w /gemini-cli ^
  --network host ^
  ubuntu:22.04 bash -c "apt-get update && apt-get install -y python3 nodejs curl sudo && useradd -m experimenter && chown -R experimenter /gemini-cli && su - experimenter -c 'cd /gemini-cli && bash'"
