import os
import subprocess
import smtplib
import datetime
from email.message import EmailMessage
import requests

# Check if config.py exists and import settings
if os.path.exists("config.py"):
    from config import (
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


def send_email(subject, content):
    """
    Send an email using the provided subject and content.
    """
    try:
        print(f"{subject}")

        email_content = content + "\n\n----==== SERVER LOGS ====----\n"

        if os.path.exists("log-python.txt"):
            with open("log-python.txt", "r", encoding="utf-8") as file:
                email_content += (
                    "\nLog from the python script: \n" + file.read() + "\n\n"
                )

        if os.path.exists("log-cmd.txt"):
            with open("log-cmd.txt", "r", encoding="utf-8") as file:
                email_content += (
                    "\nLog from the cmd commands pipe: \n" + file.read() + "\n\n"
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

        with smtplib.SMTP_SSL(
            EMAIL_SETTINGS["smtp_server"], EMAIL_SETTINGS["smtp_port"]
        ) as server:
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


def run_command(command, description):
    """
    Run a shell command and return its output.
    If the command fails, an email is sent with the error.
    """
    # Append output to log-cmd.txt. This will be sent via email.
    process = subprocess.Popen(
        command + " >> log-cmd.txt", stdout=subprocess.PIPE, shell=True
    )

    while process.poll() is None:  # check if the process is still alive
        out = process.stdout.readline()  # if it is still alive, grab the output
        if out.decode != "":
            print(out.decode(), end="")

    if process.returncode != 0:
        # Handle the error (e.g., call another function)
        send_email(
            f"Backup Command Error: {description}", "The command was:\n" + command
        )
    return process.returncode


def mount_network_share():
    """
    Check if network share is mounted. If not, mount the network share.
    """
    if ENABLED_FEATURES.get("mount_network_share", False):
        if not os.path.exists(NETWORK_SHARE["drive_letter"]):
            print("Network share wasn't mounted - Mounting Network Share")
            run_command(
                f"net use {NETWORK_SHARE['drive_letter']} {NETWORK_SHARE['path']}",
                "Mounting Network Share",
            )
    else:
        print("Skipping network share mount as it's disabled in the configuration.")


def sql_backup():
    """
    Run the SQL backup command and generate both .zbcp and .log files.
    """
    if ENABLED_FEATURES.get("perform_sql_backup", False):
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")

        backup_file = f"{SQL_BACKUP_SETTINGS['sql_backup_path']}/{SQL_BACKUP_SETTINGS['backup_name_prefix']}{date_str}.zbcp"

        print(f"Backing up SQL Database to {backup_file}")
        command = f"{ZBACKUP_CONFIG['zbackup_executable_path']} out -s {ZBACKUP_CONFIG['sql_server']} -d {ZBACKUP_CONFIG['database_name']} -u {ZBACKUP_CONFIG['sql_username']} -p {ZBACKUP_CONFIG['sql_password']} -f {backup_file}"
        run_command(command, "SQL Backup with ZBackup")
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
    command = f'rclone sync "{src}" "{dest}" --create-empty-src-dirs -v --log-file=log-rclone.txt'
    if BACKUP_SETTINGS.get("rclone_bandwidth_limit"):
        command += f' --bwlimit={BACKUP_SETTINGS["rclone_bandwidth_limit"]}'
    run_command(command, f"Backing up {src} to {dest}")
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
