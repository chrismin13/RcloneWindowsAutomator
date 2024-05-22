@echo off
setlocal enabledelayedexpansion

echo %DATE% %TIME% - Starting script
echo %CD%
echo %PATH%

REM Read the Health Check URL from healthcheck_url.txt
set /p HEALTH_CHECK_URL=<healthcheck-url.txt
echo Health check url is %HEALTH_CHECK_URL%
REM Delete the log-python.txt file if it exists
if exist log-python.txt (
    echo Deleting log-python.txt
    del log-python.txt
    if exist log-python.txt (
        REM If deletion fails, send an email with the output
        echo Failed to delete log-python.txt before backing up, sending email
        python send-email.py
        exit /b 1
    )
)

REM Run python script and capture output
echo Running python backup script
python backup.py > log-python.txt 2>&1
set RC=%errorlevel%

REM If the script fails, send an email with the output
if %RC% neq 0 (
    echo Failed to run backup, sending email.
    python send-email.py
) else (
    REM Inform healthchecks.io that the backup was successful
    echo Backup was successful
    curl -m 10 --retry 5 !HEALTH_CHECK_URL!
)

endlocal
