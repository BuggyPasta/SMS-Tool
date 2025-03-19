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

- Debian 12 (or compatible Linux distribution)
- Docker and Docker Compose
- Dockge (for deployment)
- Python 3.x
- Gammu

## Installation on Debian 12

1. Install system dependencies:
```bash
sudo apt update
sudo apt install -y python3 python3-pip gammu
```

2. Install Gammu:
```bash
sudo apt install -y gammu
```
For detailed Gammu installation instructions, visit: https://linux-packages.com/debian-12-bookworm/package/gammu

3. Configure Gammu:
```bash
sudo gammu-config
```
- Select your modem device (usually /dev/ttyUSB0)
- Choose the appropriate connection type (usually AT)
- Save the configuration

4. Test Gammu:
```bash
sudo gammu identify
```

## Project Structure

```
SMS-Tool/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── routes.py
│   ├── services.py
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   ├── icons/
│   │   │   ├── admin.svg
│   │   │   ├── dashboard.svg
│   │   │   ├── database.svg
│   │   │   ├── delete.svg
│   │   │   ├── edit.svg
│   │   │   ├── exit.svg
│   │   │   ├── modem.svg
│   │   │   ├── network.svg
│   │   │   ├── queue.svg
│   │   │   ├── report.svg
│   │   │   ├── sim.svg
│   │   │   ├── sms_delete.svg
│   │   │   ├── sms_edit.svg
│   │   │   ├── sms_send.svg
│   │   │   ├── template.svg
│   │   │   └── user.svg
│   │   └── js/
│   │       └── main.js
│   ├── templates/
│   │   ├── 404.html
│   │   ├── 500.html
│   │   ├── admin_dashboard.html
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── manage_templates.html
│   │   ├── manage_users.html
│   │   ├── send_sms.html
│   │   ├── sms_report.html
│   │   └── user_dashboard.html
│   └── services/
│       └── gammu_service.py
├── database/
│   └── schema.sql
├── docker/
│   └── gammu/
│       └── gammurc
├── logs/
├── .env
├── .env.example
├── .gitattributes
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── LICENSE
├── README.md
└── requirements.txt
```

## Deployment with Dockge

1. Open Dockge in your browser, add the new stack using the contents of the docker-compose file. Adjust the volume paths to match your system.

2. Add the contents of the `.env` file

3. Edit the contents of the `.env` file:
- Set a secure `SECRET_KEY` (you can use an online secure key generator)
- Adjust other settings as needed

4. Deploy

## Configuration

### Volume Paths
Update the volume paths in `docker-compose.yml` to match your system:
```yaml
volumes:
  - /path/to/your/database:/app/database
  - /path/to/your/logs:/app/logs
  - ./docker/gammu/gammurc:/root/.gammurc
```

### Modem Device
Ensure the modem device path in `docker-compose.yml` matches your system:
```yaml
devices:
  - /dev/ttyUSB0
```

## Default Credentials

- Admin username: `admin`
- Admin password: `admin` (change this immediately after first login)

## Security Considerations

1. Change the default admin password immediately after deployment
2. Use HTTPS in production
3. Regularly update dependencies
4. Monitor logs for suspicious activity
5. Keep the system and Gammu updated

The app is designed to be used in a LAN only and accessed via WireGuard or other VPN. 

## Troubleshooting

### Common Issues

1. Modem Not Detected
   - Check USB connection
   - Verify device permissions
   - Check Gammu configuration

2. SIM Card Issues
   - Verify SIM card is properly inserted
   - Check SIM card PIN status
   - Verify network registration

3. Permission Issues
   - Ensure proper permissions on volume mounts
   - Check Docker user permissions
   - Verify Gammu configuration file permissions

### Logs

- Application logs: `/app/logs/app.log`
- Gammu logs: `/app/logs/gammu.log`
- Docker logs: `docker logs sms-tool`

For issues and feature requests, please create an issue in the GitHub repository.

## License

AGPL-3.0 license

## Authors
BuggyPasta, with lots of help from A.I. because BuggyPasta is otherwise WORTHLESS in programming

## Acknowledgments
Vectors and icons by Mary Akveo in PD License via SVG Repo

## Future development
None planned, which is why you see in the docker compose above the 2 last lines instructing Watchtower to not bother checking for any updates. If you are not running Watchtower, feel free to remove them.

## VERY IMPORTANT NOTE. NO, SERIOUSLY.
This app is designed to work ONLY ON A LOCAL environment and is NOT secured in any way to work exposed to the Internet. As it will contain sensitive personal data, remember that you use it at your own risk. I STRONGLY recommend that you DO NOT EXPOSE it publically.

