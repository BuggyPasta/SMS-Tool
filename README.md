# SMS Sending Application

A Flask-based web application for sending SMS messages using a GSM modem. This application provides a user-friendly interface for sending SMS messages, managing templates, and monitoring message delivery status.

## Features

- User authentication with admin and regular user roles
- SMS template management
- Real-time message status tracking
- System health monitoring dashboard
- Dark/light mode support
- Mobile-responsive design
- Comprehensive error handling and logging
- Rate limiting for SMS sending
- Message validation to prevent spam
- Detailed SMS reporting with:
  - Message history tracking
  - Filtering by date range
  - Message preview functionality
  - Secure message deletion
- Optimized for UK mobile numbers (07XXXXXXXXX format)
  - Note: While the application is currently optimized for UK numbers, it may be compatible with other formats with appropriate modifications

## Hardware Requirements

- GSM Modem:
  - Primary tested device: Waveshare SIM7600E-H 4G DONGLE
  - Other potentially compatible modems (untested):
    - Huawei E3372h-320
    - Quectel EC25
    - Sierra Wireless MC7304
    - Telit LE910C1
  - Note: While other Gammu-compatible modems may work, they have not been tested with this application
- SIM card with active service
- USB connection to host system

## Software Requirements

- Docker and Docker Compose
- Linux-based system (tested on Ubuntu/Debian)
- USB port for GSM modem
- Internet connection for initial setup

## Host System Configuration

Before deploying the application, you need to configure the host system to properly handle the USB modem:

1. **Install Required System Packages**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y usbutils gammu
   ```

2. **Configure Gammu**:
   ```bash
   # Create Gammu configuration file
   sudo nano /etc/gammurc
   ```
   Add the following content:
   ```ini
   [gammu]
   device = /dev/ttyUSB3
   connection = at
   ```

3. **Set Up User Permissions**:
   ```bash
   # Add your user to the dialout group
   sudo usermod -a -G dialout $USER
   ```

4. **Identify Your Modem**:
   ```bash
   # List USB devices to find your modem
   lsusb
   
   # Check which ttyUSB device was created
   dmesg | grep ttyUSB
   ```
   Note: The modem typically appears as /dev/ttyUSB3

5. **Set USB Device Permissions**:
   ```bash
   # Set permissions for the USB device
   sudo chmod 666 /dev/ttyUSB3
   ```

6. Log out and log back in for the group changes to take effect

## USB Device Handling

Important notes about USB handling in this application:

1. The application currently requires a specific USB port configuration:
   - The modem must be connected to the port that appears as /dev/ttyUSB3
   - If using a different port, update the USB_DEVICE environment variable in docker-compose.yml

2. When the modem is connected:
   - The application performs regular health checks every 30 seconds
   - These checks verify:
     - Database connectivity
     - Modem status and model information
     - SIM card status
     - Network signal strength

3. Each SMS send attempt includes:
   - Rate limit verification
   - Phone number format validation
   - Message content validation
   - Fresh modem connection check
   - Detailed error logging

4. If you need to use a different USB port:
   - Update the USB_DEVICE environment variable in docker-compose.yml
   - Restart the container for the changes to take effect

## Deployment with Dockge

1. In Dockge, create a new stack and paste the following docker-compose.yml:
   ```yaml
   version: '3.8'

   services:
     sms-tool:
       build:
         context: https://github.com/BuggyPasta/SMS-Tool.git
         dockerfile: Dockerfile
       container_name: sms-tool
       restart: unless-stopped
       privileged: true
       ports:
         - "4001:4001"
       volumes:
         - ${BASE_PATH}/instance:/app/instance:rw
         - ${BASE_PATH}/logs:/app/logs:rw
         - /etc/gammurc:/etc/gammurc:ro
         - /dev:/dev:rw
       group_add:
         - dialout
         - tty
       environment:
         - FLASK_APP=app
         - FLASK_ENV=production
         - SECRET_KEY=${SECRET_KEY}
         - ADMIN_PASSWORD=${ADMIN_PASSWORD}
         - TZ=${TZ:-Europe/London}
         - DATABASE_PATH=${DATABASE_PATH}
         - LOG_LEVEL=${LOG_LEVEL:-INFO}
         - GAMMU_CONFIG=${GAMMU_CONFIG:-/etc/gammurc}
         - PYTHONUNBUFFERED=1
         - USB_DEVICE=/dev/ttyUSB3
         - FLASK_RUN_HOST=0.0.0.0
         - FLASK_RUN_PORT=4001
       healthcheck:
         test: ["CMD-SHELL", "curl -s -f http://localhost:4001/health || exit 1"]
         interval: 30s
         timeout: 10s
         retries: 3
         start_period: 60s
       cap_add:
         - SYS_ADMIN
         - MKNOD
       security_opt:
         - seccomp:unconfined
       stop_grace_period: 30s
       labels:
         - "com.centurylinklabs.watchtower.enable=false"
   ```

   Note: DO NOT modify the docker-compose.yml file. All configuration should be done through the .env file.

2. Create a `.env` file in your stack with the following variables:
   ```ini
   # Security settings (REQUIRED)
   SECRET_KEY=your_secret_key_here  # Use a random string of 32 characters or more
   ADMIN_PASSWORD=your_admin_password_here  # Use a strong password for the admin login

   # Application settings
   TZ=Europe/London  # Optional - defaults to Europe/London if not set
   DATABASE_PATH=/app/instance/database.db  # DO NOT CHANGE - this is the internal container DB path
   LOG_LEVEL=INFO  # Optional - defaults to INFO if not set
   GAMMU_CONFIG=/etc/gammurc  # DO NOT CHANGE - this is the host's Gammu config path
   BASE_PATH=/home/YOUR_USER_FOLDER/sms-tool  # Required - path where application data will be stored
   ```

   Note: Only SECRET_KEY, ADMIN_PASSWORD, and BASE_PATH need to be modified. The other variables have sensible defaults or must not be changed.

3. Deploy the stack in Dockge
   - The application will automatically:
     - Pull the code from GitHub
     - Build the container
     - Create necessary directories
     - Initialize the database
     - Configure the Gammu service

4. Access the application at `http://your-server:4001`
   - Log in with:
     - Username: admin
     - Password: [the password you set in ADMIN_PASSWORD]

## Directory Structure

```
.
├── app/
│   ├── static/
│   ├── templates/
│   ├── services/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── exceptions.py
│   ├── init_db.py
│   ├── logging_config.py
│   ├── models.py
│   ├── preflight.py
│   └── routes.py
├── database/
│   └── schema.sql
├── docker/
│   └── gammu/
│       └── gammurc
├── .git/
├── .gitattributes
├── .gitignore
├── LICENSE
├── README.md
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── prepare_host.sh
└── requirements.txt
```

## Backup and Restore

All persistent data is stored in the volumes defined in your docker-compose.yml:
- `${BASE_PATH}/instance`: Contains the SQLite database
- `${BASE_PATH}/logs`: Contains application logs
  - `app.log`: Application events and errors
  - `gammu.log`: Modem communication logs

To backup your data, simply archive the directory specified in your BASE_PATH environment variable.

## Changing Configuration

You can modify most environment variables in the .env file without needing to rebuild or re-download the application:

1. **SECRET_KEY**: Can be changed at any time
   - Users will need to log in again
   - No data is lost
   - Just update the value and redeploy

2. **ADMIN_PASSWORD**: Can be changed at any time
   - Takes effect immediately after redeploy
   - Existing sessions remain valid

3. **Other Settings**: TZ, LOG_LEVEL can be changed freely
   - Take effect after redeployment
   - No impact on stored data

Note: Never change DATABASE_PATH, GAMMU_CONFIG, or paths in docker-compose.yml as these could break the application.

## Troubleshooting

1. If the application fails to start:
   - Check the logs at `/home/YOUR_USER_FOLDER/sms-tool/logs/app.log`
   - Verify the GSM modem is properly connected
   - Ensure all required directories exist
   - Verify that Gammu is installed on the host system and configured at `/etc/gammurc`
   - Check that host system USB permissions are properly configured

2. If SMS sending fails:
   - Check the modem status in the admin dashboard
   - Verify the SIM card is properly inserted and activated
   - Check the signal strength indicator
   - Verify the USB device permissions on the host system
   - Check if the modem has been moved to a different USB port
   - Review the rate limiting settings if sending multiple messages
   - Verify that the Gammu configuration at `/etc/gammurc` is correct

## Security Considerations

This application is designed for LOCAL NETWORK USE ONLY. Important security notes:

1. The application requires privileged access to USB devices
2. The container has access to all USB devices on the host system
3. DO NOT expose this application to the internet
4. The application contains sensitive data and should only be accessed within your secure local network
5. All SMS messages are stored in an encrypted database
6. Rate limiting is enforced to prevent abuse

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Authors
BuggyPasta, with lots of help from A.I. because BuggyPasta is otherwise WORTHLESS in programming

## Acknowledgments
Vectors and icons by Mary Akveo in PD License via SVG Repo

## Future development
None planned, which is why you see in the docker compose the 2 last lines instructing Watchtower to not bother checking for any updates. If you are not running Watchtower, feel free to remove them.

## VERY IMPORTANT NOTE. NO, SERIOUSLY.
This app is designed to work ONLY ON A LOCAL environment and is NOT secured in any way to work exposed to the Internet. As it will contain sensitive personal data, remember that you use it at your own risk. I STRONGLY recommend that you DO NOT EXPOSE it publically.

