# Telegram Bot for Monitoring and Scanning

A Telegram bot for monitoring routers, scanning networks, and searching for miners, with advanced configuration and SNMP support.

## 🚀 Features

### Core Functions
- **🌐 Router Monitoring** – Check the status of routers by IP and port
- **🔍 Network Scanning** – Discover devices in a specified network
- **⛏️ Miner Search** – Specialized scan for miners (port 4028)
- **⚡ Fast Scan** – Parallel scanning for speed
- **📊 Statistics** – Track usage and results
- **🔔 Notifications** – Notification system with importance levels
- **⚙️ Settings** – Full-featured settings management
- **🌐 SNMP Routers** – SNMP status and diagnostics for routers (see below)
- **🌍 Localization** – Full support for multiple languages (English, Russian, German, Dutch, Chinese)

### SNMP Router Monitoring
- **SNMP Routers Menu** in the main menu
- **Quick SNMP Status**: sysName, sysDescr, sysUpTime for all routers
- **Extended SNMP Query**: Detailed info per router (sysName, sysDescr, sysUpTime, sysContact, sysLocation, ifNumber, and interface list)
- **Community String Management**: Change SNMP community string via the bot
- **CSV Export**: Download full interface list as CSV
- **Async SNMP Polling**: Fast, robust, and user-friendly
- **Localized messages and error handling**

### Settings System
The bot includes a powerful settings system allowing you to change all parameters:

#### 🌐 Monitoring
- Router check interval (30 sec – 1 hour)
- Auto-start monitoring
- Status change notifications
- Startup notifications

#### 🔔 Notifications
- Enable/disable notifications
- Quiet hours (configurable time)
- Notification levels (info, warning, critical, success)
- Quiet hours time window

#### 🔍 Scanning
- Scan timeout
- Max concurrent scans
- Ports to scan
- Special ports for miners and routers
- Scan results TTL

#### 🌐 Routers
- Router IPs for monitoring
- Router ports for checking
- Router check interval
- Router status

#### 🎨 Interface
- Interface language
- Show scan progress
- Show timestamps
- Compact mode

#### 🔒 Security
- Allowed users list
- Admin-only settings
- Logging level
- Bot token management

#### 💾 Backup
- Automatic backups
- Backup interval
- Max number of backups
- Manual backup creation

#### 📊 Export/Import
- Export settings to JSON
- Import settings from JSON
- Export statistics
- Export logs

## 📋 Commands

### Main Commands
- `/start` or `/menu` – Open the main menu of the bot.
- `/help` – Show help and usage instructions.
- `/status` – Show the current status of the bot (active scans, monitoring, routers, etc.).
- `/stats` – Show usage and scan statistics.
- `/role` – Show your current role (admin, operator, user) in the system.

### Monitoring Commands
- `/monitor_start` – Start background router monitoring.
- `/monitor_stop` – Stop background monitoring.

### Export Commands
- `/export_stats` – Export statistics as CSV (if enabled).

### Menu Navigation
Most features (scanning, settings, notifications, backup, etc.) are available via the bot's menu buttons. Use `/start` or `/menu` to open the main menu and navigate using the provided buttons.

## ⚙️ Setup

### Install dependencies
```bash
pip install -r requirements.txt
```

### Configuration
1. Create the file `telegram_bot/data/settings.json`:
```json
{
  "routers": {
    "ips": ["11.250.0.1", "11.250.0.2", "11.250.0.3", "11.250.0.4", "11.250.0.5"],
    "ports": [8080, 8022, 80, 22]
  },
  "scanning": {
    "default_timeout": 5,
    "max_concurrent_scans": 3,
    "results_ttl": 3600
  },
  "monitoring": {
    "auto_start": true,
    "interval": 300
  }
}
```
2. Create the file `telegram_bot/data/secrets.json`:
```json
{
  "TELEGRAM_BOT_TOKEN": "your-bot-token-here",
  "CHAT_ID": 123456789
}
```

### Run the bot
```bash
python -m telegram_bot.bot.main
```

## 🎯 Settings System

Settings are available via the "⚙️ Settings" button in the main menu.

### Settings Categories

#### 🌐 Monitoring
- **Monitoring interval**: 30 seconds to 1 hour
- **Auto-start**: Start monitoring automatically on bot launch
- **Status change notifications**: Notify on router status changes
- **Startup notifications**: Notify when monitoring starts

#### 🔔 Notifications
- **Enable/disable**: General notification control
- **Quiet hours**: No notifications during this period
- **Notification levels**: Set importance of notifications
- **Quiet hours time**: Configure quiet period

#### 🔍 Scanning
- **Scan timeout**: Device response wait time
- **Max concurrent scans**: Number of parallel scans
- **Ports to scan**: List of ports to check
- **Miner ports**: Special ports for miner search
- **Router ports**: Ports for router checks
- **Results TTL**: Scan results retention time

#### 🌐 Routers
- **Router IPs**: List of IPs for monitoring
- **Router ports**: Ports for router checks
- **Check interval**: Router check frequency
- **Router status**: Current router state

#### 🎨 Interface
- **Language**: Bot language selection
- **Show progress**: Show scan progress
- **Show time**: Show timestamps
- **Compact mode**: Shortened output

#### 🔒 Security
- **Allowed users**: List of users with access
- **Admin-only settings**: Restrict settings to admins
- **Logging level**: Log detail level
- **Change token**: Update bot token

#### 💾 Backup
- **Auto-backup**: Automatic backup creation
- **Backup interval**: Backup frequency
- **Max backups**: Limit of stored backups
- **Create backup now**: Manual backup

#### 📊 Export/Import
- **Export settings**: Save settings to JSON
- **Import settings**: Load settings from JSON
- **Export statistics**: Save statistics
- **Export logs**: Save logs

### Managing Settings

#### View settings
- **Summary**: Quick overview of all settings
- **Detailed view**: By category

#### Change settings
- **Via buttons**: For simple settings (on/off, select from list)
- **Via input**: For numbers and lists

#### Reset settings
- **Reset to defaults**: Restore default settings

#### Export/Import
- **Export**: Save current settings
- **Import**: Load settings from file

## 🧪 Testing

### Test settings system
```bash
python test_settings_system.py
```

### Test help system
```bash
python test_help_system.py
```

### Test new features
```bash
python test_new_features.py
```

## 📁 Project Structure

```
telegram_bot/
├── bot/
│   ├── __init__.py
│   ├── main.py            # Bot entry point
│   ├── keyboards.py       # Keyboards
│   ├── translations.py    # Localization
├── utils/
│   ├── __init__.py
│   ├── background_monitor.py    # Background monitoring
│   ├── notifications.py         # Notification system
│   ├── statistics.py            # Statistics
│   ├── help_system.py           # Help system
│   ├── settings_manager.py      # Settings system
│   ├── router_monitor.py        # Router monitoring
│   ├── network_scan.py          # Network scanning
│   ├── miner_scan.py            # Miner scanning
│   ├── fast_scan.py             # Fast scanning
│   ├── markdown_utils.py        # Markdown utilities
│   ├── snmp_utils.py            # SNMP router support
│   ├── scan_manager.py          # Scan manager
├── data/                        # Data directory
├── requirements.txt             # Dependencies
├── README.md                    # Documentation
└── test_*.py                    # Test scripts
```

## 🔧 Technical Details

### Asynchronous Scanning
- Uses `asyncio` for non-blocking scans
- Supports parallel and sequential scanning
- Real-time progress bars

### Notification System
- Importance levels: info, warning, critical, success
- Notification types: system_alert, scan_completed, scan_error, router_status_change
- Quiet hours support

### Statistics
- Tracks user commands
- Scan statistics
- Router statistics
- Export to CSV

### Settings System
- JSON file for settings storage
- Automatic creation of default settings
- Value validation
- Export/import settings
- Reset to defaults

### SNMP Router Support
- SNMP polling via system `snmpget`/`snmpwalk` (no Python SNMP dependencies required)
- Async SNMP queries for performance
- Quick and extended SNMP status
- Community string management
- CSV export for interface lists
- Localized error and status messages
- Robust error handling (timeouts, no response, etc.)

## 🚀 Roadmap

- [ ] Web interface for management
- [ ] Integration with monitoring systems (Zabbix, Nagios)
- [x] SNMP support
- [x] Extended analytics
- [x] Multilanguage support
- [ ] API for external systems
- [ ] Database integration
- [ ] Plugin system

## 📝 License

MIT License

## 🤝 Support

For help, use the `/help` command in the bot or create an issue in the project repository. 