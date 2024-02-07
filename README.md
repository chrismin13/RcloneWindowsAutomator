# Rclone Windows Automator
A convenient Python and Windows Batch based tool to automate backup management with Rclone and ZBackup.

Functionality:
- Sync **one way** specific folders to another drive (you could always change the rclone command but it hasn't been tested)
- Mount network drives automatically before copying
- Backup Microsoft SQL Server databases with ZBackup (only tested with Soft1 products) and delete older database backups
- **Send emails with logs** in case of any errors
- Monitor scripts status with **healthchecks.io** integration
- Designed to run from a daily task in Task Scheduler

# Setup
Run the `setup.cmd` file to install Python, Rclone and the required libraries.
Copy the example-config.py file and rename it to config.py. Then, follow the comments in the file to set it up according to your needs. Run the script by running the cmd file.