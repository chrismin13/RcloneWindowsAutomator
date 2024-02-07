@echo off
setlocal enabledelayedexpansion

REM Read the Health Check URL from healthcheck_url.txt
set /p HEALTH_CHECK_URL=<healthcheck-url.txt

REM Run python script and capture output
python backup.py > log-python.txt 2>&1
set RC=%errorlevel%

REM If the script fails, send an email with the output
if not %RC%==0 (
    python send-email.py
) else (
    REM Inform healthchecks.io that the backup was successful
    curl -m 10 --retry 5 !HEALTH_CHECK_URL!
)
