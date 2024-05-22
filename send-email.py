import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import datetime
import requests

# Check if config.py exists and import settings
if os.path.exists("config.py"):
    from config import (
        EMAIL_SETTINGS,
        SQL_BACKUP_SETTINGS,
        HEALTH_CHECK_URL,
    )
else:
    print("Error: config.py does not exist. Please ensure the configuration file is in the same directory as this script.")
    exit(1)

try:
    # Use SMTP server configuration from config.py
    smtp_server = EMAIL_SETTINGS['smtp_server']
    smtp_port = EMAIL_SETTINGS['smtp_port']  # For starttls, adjust as needed in config.py

    # Sender and receiver email addresses from config.py
    sender_email = EMAIL_SETTINGS['email_from']
    sender_password = EMAIL_SETTINGS['email_password']
    receiver_email = EMAIL_SETTINGS['email_to']

    # File to be sent, adjust zbackup_log path according to config.py
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    zbackup_log = f"{SQL_BACKUP_SETTINGS['sql_backup_path']}/{SQL_BACKUP_SETTINGS['backup_name_prefix']}{date_str}.log"
    attachment_file_paths = ['log-python.txt', "log-cmd.txt", "log-rclone.txt", zbackup_log, "log-task.txt"] # Add more files here if needed

    # Create a multipart message and set headers
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = receiver_email
    message['Subject'] = f"{EMAIL_SETTINGS['machine_name']} - Python Script Failure"

    for attachment_file_path in attachment_file_paths:
        # Open the file in binary mode
        if os.path.exists(attachment_file_path):
            with open(attachment_file_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())

            # Encode the file in ASCII characters to send by email    
            encoders.encode_base64(part)

            # Add header as pdf attachment
            part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_file_path))

            # Add attachment to message
            message.attach(part)
            print("Added " + attachment_file_path + " as an attachment")

    text = message.as_string()

    # Log in to the server using secure context and send email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, text)
        print("Sent email")
except Exception as e:
    # Save a log file with the error and send a healthchecks.io failure
    log_file = (
        "send-email-error-"
        + datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        + ".txt"
    )
    with open(log_file, "w") as f:
        f.write(str(e))
    requests.get(HEALTH_CHECK_URL + "/fail", timeout=10)
    raise SystemExit(1)
