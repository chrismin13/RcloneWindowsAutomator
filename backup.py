print("Welcome to the backup script. Importing dependencies.")

import os
import subprocess
import smtplib
import datetime
from email.message import EmailMessage
import requests
import locale

print(os.getcwd())

print("Importing config variables")

# Check if config.py exists and import settings
if os.path.exists("config.py"):
    from config import (
        VERSION,
        ENABLED_FEATURES,
        EMAIL_SETTINGS,
        HEALTH_CHECK_URL,
        NETWORK_SHARE,
        BACKUP_SETTINGS,
        SQL_BACKUP_SETTINGS,
        ZBACKUP_CONFIG,
        BACKUP_RETENTION,
    )
else:
    print(
        "Error: config.py does not exist. Please ensure the configuration file is in the same directory as this script."
    )
    exit(1)

if VERSION != 2:
    print("Error: The config file is not up to date. Please check the GitHub page for instructions on updating the config file.")
    print("https://github.com/chrismin13/RcloneWindowsAutomator/wiki/Updating-the-config-file")


def send_email(subject, content):
    """
    Send an email using the provided subject and content.
    """
    try:
        # Print summary of issue
        print(subject )

        email_content = content + "\n\n----==== SERVER LOGS ====----\n"
        
        if os.path.exists("log-python.txt"):
            with open("log-python.txt", "r", encoding="utf-8") as file:
                email_content += (
                    "\nLog from the python script: \n" + file.read() + "\n\n"
                )

        if os.path.exists("log-cmd.txt"):
            with open("log-cmd.txt", "r", encoding="utf-8") as file:
                email_content += (
                    "\nLog of commands: \n" + file.read() + "\n\n"
                )

        if os.path.exists("log-rclone.txt"):
            with open("log-rclone.txt", "r", encoding="utf-8") as file:
                email_content += "\nLog from rclone: \n" + file.read() + "\n\n"

        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        zbackup_log = f"{SQL_BACKUP_SETTINGS['sql_backup_path']}/{SQL_BACKUP_SETTINGS['backup_name_prefix']}{date_str}.log"

        if os.path.exists(zbackup_log):
            with open(zbackup_log, "r", encoding="utf-8") as file:
                email_content += "\nLog from Zbackup: \n" + file.read() + "\n\n"

        msg = EmailMessage()
        msg.set_content(email_content)
        msg["Subject"] = EMAIL_SETTINGS["machine_name"] + " - " + subject
        msg["From"] = EMAIL_SETTINGS["email_from"]
        msg["To"] = EMAIL_SETTINGS["email_to"]

        with smtplib.SMTP(
            EMAIL_SETTINGS["smtp_server"], EMAIL_SETTINGS["smtp_port"]
        ) as server:
            server.starttls()
            server.login(
                EMAIL_SETTINGS["email_username"], EMAIL_SETTINGS["email_password"]
            )
            server.send_message(msg)
    except Exception as e:
        print("Failed to send email: " + str(e))
        # Log the exception to a log file titled with the current date and time
        log_file = (
            "email-error-"
            + datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            + ".txt"
        )
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(str(e) + "\n\n" + subject + "\n\n" + email_content)
        requests.get(HEALTH_CHECK_URL + "/fail", timeout=10)

    raise SystemExit(1)


def run_command(command, description, timeout):
    """
    Run a shell command and return its output.
    If the command fails, an email is sent with the error.
    """
    # Must determine encoding to ensure that the output is readable for systems with different languages.
    encoding = os.device_encoding(1)
    
    # Encoding might be none if the command is run from task scheduler
    if not encoding:
        # Greek encoding
        if locale.getencoding() == "cp1253":
            encoding = "cp737"
        # English encoding
        else:
            encoding = "cp437"
        # Can be updated to include more locales.
    
    print(f'Current shell encoding is {encoding}')
    
    # Append stdout to stdout.txt and stderr to std-err.txt.
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) # shell=True has been removed as no shell commands were used and it isn't recommended
    
    timeout_over=False
    # Wait for command to complete up to the timeout (integer in seconds)
    try:
        output, errors = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timeout_over = True
        process.kill()
        output, errors = process.communicate()
    
    # Save output and errors to a single log-cmd.txt file in utf 8
    with open("log-cmd.txt", "a", encoding="utf-8") as file:
        file.write(f"\n\nRan Command: {command}\n")
        file.write(f"Description: {description}\n")
        file.write(f"Output: {output.decode(encoding)}\n")
        file.write(f"Errors: {errors.decode(encoding)}\n")
    
    if timeout_over:
        print(f"Error: {description} timed out after {timeout} seconds")
        send_email("Command Timeout", f"Error: {description} timed out after {timeout} seconds")
        return 1
    
    if process.returncode != 0: # Program ran into an error
        print(f"Error: {description} failed with exit code {process.returncode}")
        send_email("Command Error", f"Error: {description} failed with exit code {process.returncode}")
    return process.returncode


def mount_network_share():
    """
    Check if network share is mounted. If not, mount the network share.
    """
    if ENABLED_FEATURES.get("mount_network_share", False):
        print("Attempting to mount network share")
        if not os.path.exists(NETWORK_SHARE["drive_letter"]):
            print("Network share wasn't mounted - Mounting Network Share")
            run_command(
                f"net use {NETWORK_SHARE['drive_letter']} {NETWORK_SHARE['path']} /user:{NETWORK_SHARE['username']} {NETWORK_SHARE['password']}",
                "Mounting Network Share",
                timeout=15
            )
    else:
        print("Skipping network share mount as it's disabled in the configuration.")


def sql_backup():
    """
    Run the SQL backup command and generate both .zbcp and .log files.
    """
    if ENABLED_FEATURES.get("perform_sql_backup", False):
        print("Attempting to backup SQL")
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")

        backup_file = f"{SQL_BACKUP_SETTINGS['sql_backup_path']}/{SQL_BACKUP_SETTINGS['backup_name_prefix']}{date_str}.zbcp"

        print(f"Backing up SQL Database to {backup_file}")
        command = f"{ZBACKUP_CONFIG['zbackup_executable_path']} out -s {ZBACKUP_CONFIG['sql_server']} -d {ZBACKUP_CONFIG['database_name']} -u {ZBACKUP_CONFIG['sql_username']} -p {ZBACKUP_CONFIG['sql_password']} -f {backup_file}"
        run_command(command, "SQL Backup with ZBackup", timeout=None)
    else:
        print("Skipping SQL backup as it's disabled in the configuration.")


def prune_old_backups():
    """
    Go through the SQL backups and retain:
    - All backups from the last 30 days.
    - At least one backup from each previous month if specified.
    """
    if ENABLED_FEATURES.get("prune_old_backups", False):
        print("Pruning old SQL backups")
        now = datetime.datetime.now()
        backup_dir = SQL_BACKUP_SETTINGS["sql_backup_path"]
        seen_months = set()

        # Ensure the backup directory exists to prevent errors
        if not os.path.exists(backup_dir):
            print(f"Backup directory does not exist: {backup_dir}")
            send_email(
                "Backup Error",
                f"Backup directory does not exist: {backup_dir}",
            )

        # List all SQL backup files in the directory
        all_backups = sorted(
            [
                f
                for f in os.listdir(backup_dir)
                if f.startswith(SQL_BACKUP_SETTINGS["backup_name_prefix"])
                and f.endswith(".zbcp")
            ],
            reverse=True,
        )

        for backup_file in all_backups:
            # Extract the date from the backup file name
            file_date_str = backup_file[
                len(SQL_BACKUP_SETTINGS["backup_name_prefix"]) : -5
            ]
            try:
                file_date = datetime.datetime.strptime(file_date_str, "%Y-%m-%d")
            except ValueError:
                # Skip files that do not match the expected naming convention
                continue

            days_diff = (now - file_date).days
            month_key = file_date.strftime("%Y-%m")

            # Determine if the backup should be deleted
            if days_diff > BACKUP_RETENTION["days_to_keep"]:
                if (
                    month_key in seen_months
                    or not BACKUP_RETENTION["keep_first_of_month"]
                ):
                    full_path = os.path.join(backup_dir, backup_file)
                    os.remove(full_path)
                    print(f"Deleted old backup: {backup_file}")
                else:
                    seen_months.add(month_key)
    else:
        print("Skipping pruning of old backups as it's disabled in the configuration.")


def backup_directory(src, dest):
    """
    Backup a directory to the specified destination using rclone.
    """
    print("Attempting to backup " + src + " to " + dest)
    command = f'rclone sync "{src}" "{dest}" --create-empty-src-dirs -v --log-file=log-rclone.txt'
    if BACKUP_SETTINGS.get("rclone_bandwidth_limit"):
        command += f' --bwlimit={BACKUP_SETTINGS["rclone_bandwidth_limit"]}'
    run_command(command, f"Backing up {src} to {dest}", timeout=None)
    if os.path.exists("log-rclone.txt"):
        # Add rclone log to the cmd log
        log_rclone = open("log-rclone.txt", "r", encoding="utf-8").read()
        with open("log-cmd.txt", "a", encoding="utf-8") as file:
            file.write(
                "\nRan Rclone command '"
                + command
                + "' with output:\n"
                + log_rclone
                + "\n\n"
            )
        os.remove("log-rclone.txt")


def main():
    print("Removing old logs")
    # Initial cleanup of old log files
    if os.path.exists("log-cmd.txt"):
        os.remove("log-cmd.txt")
    if os.path.exists("log-rclone.txt"):
        os.remove("log-rclone.txt")
    
    mount_network_share()
    sql_backup()
    prune_old_backups()

    dirs_to_backup = BACKUP_SETTINGS["directories_to_backup"]
    for dir_path in dirs_to_backup:
        backup_directory(
            dir_path, f"{BACKUP_SETTINGS['backup_destination_prefix']}{dir_path[2:]}"
        )


if __name__ == "__main__":
    main()
