# example-config.py - Template configuration for the backup script setup.

# Do not touch unless you've checked that you have upgraded according to a newer example-config.py. 
VERSION = 2

# ENABLED_FEATURES
# Control which functionalities are active. Set to False to disable specific operations.
ENABLED_FEATURES = {
    "mount_network_share": True,  # Enable or disable mounting the network share.
    "perform_sql_backup": True,  # Enable or disable SQL database backups.
    "prune_old_backups": True,  # Enable or disable pruning of old backups.
}

# EMAIL_SETTINGS
# Settings for email notifications. Replace placeholders with your actual SMTP details and email addresses.
EMAIL_SETTINGS = {
    "machine_name": "YourMachineName",  # Will be included in the subject line to identify the machine.
    "smtp_server": "smtp.example.com",
    "smtp_port": 587, # Connection must be TLS
    "email_from": "your_email@example.com",
    "email_to": "recipient_email@example.com",
    "email_username": "your_email@example.com",
    "email_password": "your_email_password",
}

# HEALTH_CHECK_URL
# URL for the health check service. The script will ping this URL after each run.
# Copy the example-healthcheck-url.txt to healthcheck-url.txt and replace the URL with your own.
# Sign up at https://healthchecks.io/ to get your own UUID.
with open('healthcheck-url.txt', 'r') as file:
    HEALTH_CHECK_URL = file.read().strip()

# NETWORK_SHARE
# Configuration for the network share. Adjust the path and drive letter according to your network setup.
NETWORK_SHARE = {
    "path": "\\\\your_network_share_path\\folder_name",
    "drive_letter": "Z:",
    "username" = "your_smb_username",
    "password" = "your_smb_password",
}

# BACKUP_SETTINGS
# Configuration for directory backups. Specify which directories to backup and the backup destination.
BACKUP_SETTINGS = {
    "directories_to_backup": [
        "C:/path/to/important/data",
        "D:/another/important/path",
        # Add more paths as needed.
        # SHOULD ALWAYS BE IN THE FORMAT "C:/path/to/dir", no relative paths.
    ],
    "backup_destination_prefix": "Z:/BackupDestination",
    "rclone_bandwidth_limit": None,  # Bandwidth limit for rclone, e.g., "10M" for 10mbps. Set to None for no limit.
}

# SQL_BACKUP_SETTINGS
# Settings for SQL database backups. Specify the local backup path and a prefix for the backup filenames.
SQL_BACKUP_SETTINGS = {
    "sql_backup_path": "C:/path/to/sql/backups",
    "backup_name_prefix": "YourBackupPrefix-",
}

# ZBACKUP_CONFIG
# ZBackup tool configuration. Adjust according to your ZBackup installation and SQL server details.
ZBACKUP_CONFIG = {
    "zbackup_executable_path": "path/to/zbackup.exe",
    "sql_server": "YourSQLServer\\Instance",
    "database_name": "YourDatabaseName",
    "sql_username": "YourSQLUsername",
    "sql_password": "YourSQLPassword",
}

# BACKUP_RETENTION
# Backup retention policy. Configure how long to keep backups and whether to keep the first backup of each month.
BACKUP_RETENTION = {
    "days_to_keep": 30,  # Number of days to keep daily backups.
    "keep_first_of_month": True,  # Whether to keep the first backup of each month indefinitely.
}
