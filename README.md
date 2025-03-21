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
- Optimized for UK mobile numbers (07XXXXXXXXX format)
  - Note: While the application is currently optimized for UK mobile numbers, it may be compatible with other number formats with appropriate modifications

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

## Deployment with Dockge

1. Clone this repository to your Dockge server:
   ```bash
   git clone https://github.com/BuggyPasta/SMS-Tool.git
   cd SMS-Tool
   ```

2. Run the preparation script to set up the host environment:
   ```bash
   chmod +x prepare_host.sh
   sudo ./prepare_host.sh
   ```

3. Ensure your user is in the dialout group (the script will remind you):
   ```bash
   sudo usermod -a -G dialout $USER
   # Log out and back in for the changes to take effect
   ```

4. Ensure your GSM modem is connected and recognized (usually as /dev/ttyUSB3)

5. Create a stack in Dockge using the provided docker-compose.yml

6. Set the following environment variables in Dockge:
   - SECRET_KEY: Your secure secret key

7. Deploy the stack

The application will:
- Use the pre-initialized database schema
- Write logs to the prepared logs directory
- Set up the SMS queue system
- Configure the Gammu service for your modem

## Directory Structure

```
.
├── app/
│   ├── static/
│   ├── templates/
│   ├── services/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── routes.py
│   └── services.py
├── database/
│   └── schema.sql
├── docker/
│   └── gammu/
│       └── gammurc
├── logs/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Backup and Restore

All persistent data is stored in `/home/ovenking/docker_backup/sms_tool/`:
- `database/`: Contains the SQLite database and schema
- `logs/`: Contains application logs

To backup your data, simply archive the `/home/ovenking/docker_backup/sms_tool/` directory.

## Troubleshooting

1. If the application fails to start:
   - Check the logs at `/home/ovenking/docker_backup/sms_tool/logs/app.log`
   - Verify the GSM modem is properly connected
   - Ensure all required directories exist and have proper permissions
   - Check that your user is in the dialout group: `groups $USER`
   - Verify the schema.sql file exists in the database directory

2. If you see permission errors:
   - Run the prepare_host.sh script again
   - Ensure you've logged out and back in after adding your user to the dialout group
   - Check directory permissions: `ls -la /home/ovenking/docker_backup/sms_tool/`

3. If SMS sending fails:
   - Check the modem status in the admin dashboard
   - Verify the SIM card is properly inserted and activated
   - Check the signal strength indicator

4. For other issues:
   - Review the application logs
   - Check the container logs in Dockge
   - Verify all environment variables are set correctly

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

