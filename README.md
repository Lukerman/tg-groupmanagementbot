# Telegram Group Management Bot

A fully working, production-ready Telegram group management bot with advanced features built using Python and python-telegram-bot v21.0.

## Features

### 🛡️ Moderation Tools
- **Ban/Unban** - Ban users with reasons, unban when needed
- **Mute/Unmute** - Temporary or permanent mutes with duration support (e.g., `/mute 5m spam`)
- **Warn System** - Warn users, auto-ban after 3 warnings
- **Kick** - Remove users without banning
- **Warnings View/Clear** - Track and manage user warnings

### 🔒 Protection Features
- **Welcome Messages** - Customizable welcome messages with {name} and {title} placeholders
- **CAPTCHA Verification** - Math-based captcha for new members
- **Anti-Flood** - Detect and mute users who send too many messages
- **Link Protection** - Auto-delete messages containing links
- **Banned Words Filter** - Block specific words/phrases

### ⚙️ Admin Commands
- `/start` - Start the bot
- `/help` - Show help message
- `/settings` - View group settings
- `/ban <user> [reason]` - Ban a user
- `/unban <user>` - Unban a user
- `/mute <user> [duration] [reason]` - Mute a user (e.g., `/mute @user 10m spam`)
- `/unmute <user>` - Unmute a user
- `/warn <user> [reason]` - Warn a user
- `/warnings <user>` - View user warnings
- `/clearwarnings <user>` - Clear all warnings
- `/kick <user>` - Kick a user
- `/info <user>` - Get user information
- `/welcome <message>` - Set welcome message
- `/captcha` - Toggle CAPTCHA
- `/antiflood <count> [window]` - Set anti-flood limit
- `/linkprotect` - Toggle link protection
- `/bannedwords add/remove/clear` - Manage banned words
- `/ping` - Check bot status

## Installation

### Prerequisites
- Python 3.9+
- pip package manager
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Setup Steps

1. **Clone or download this repository**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables:**
   ```bash
   export TELEGRAM_BOT_TOKEN='your_bot_token_here'
   export ADMIN_IDS='123456789,987654321'  # Optional: comma-separated admin IDs
   ```

4. **Run the bot:**
   ```bash
   cd src
   python bot.py
   ```

### Alternative: Using .env file
Create a `.env` file in the root directory:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
```

Then run:
```bash
pip install python-dotenv
python src/bot.py
```

## Project Structure

```
/workspace
├── data/                    # SQLite database storage
├── logs/                    # Bot logs
├── src/
│   ├── bot.py              # Main bot entry point
│   ├── database.py         # Database configuration
│   ├── db_operations.py    # Database CRUD operations
│   ├── models.py           # SQLAlchemy models
│   ├── handlers/
│   │   ├── moderation.py   # Moderation commands
│   │   ├── protection.py   # Protection features
│   │   └── permissions.py  # Permission checks
│   └── utils/
│       ├── helpers.py      # Utility functions
│       └── keyboards.py    # Inline keyboards
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Database

The bot uses SQLite for data storage. The database file is automatically created at `data/bot.db`.

### Tables:
- **groups** - Group settings and configurations
- **users** - User information
- **warnings** - Warning records
- **mutes** - Active mutes
- **bans** - Ban records
- **captcha_sessions** - CAPTCHA verification sessions
- **logs** - Action logs

## Configuration

### Group Settings (stored per group):
- Welcome message (enabled/disabled, custom text)
- CAPTCHA (enabled/disabled)
- Anti-spam (enabled/disabled)
- Anti-flood (message count, time window)
- Banned words list
- Link protection (enabled/disabled)

## Making Bot Admin

For full functionality, make the bot an administrator in your group with these permissions:
- ✅ Delete messages
- ✅ Ban users
- ✅ Restrict members
- ✅ Invite users (optional)

## Support

For issues or feature requests, please check the documentation or create an issue.

## License

MIT License - Feel free to use and modify!

---

**Note:** Replace `YourBotName` and `YourSupportChat` in the keyboard files with your actual bot username and support chat.
