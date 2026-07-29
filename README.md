# 🤖 Advanced Telegram Group Management Bot

A powerful, feature-rich Telegram group management bot with advanced moderation tools, custom themes, and inline keyboard controls.

## ✨ Features

### 🛡️ Protection
- **Anti-Spam**: Automatically detect and remove spam messages
- **Link Filter**: Delete messages containing links
- **Forward Filter**: Block forwarded messages from channels
- **CAPTCHA Verification**: Verify new members with math challenges
- **Anti-Bot**: Prevent bots from joining without approval

### 👋 Welcome System
- Custom welcome messages with HTML formatting
- Goodbye messages for leaving members
- Dynamic variables: `{mention}`, `{title}`, `{username}`, `{first_name}`
- Enable/disable via inline buttons

### ⚠️ Moderation Tools
- `/ban` - Ban users permanently
- `/mute` - Mute users temporarily (supports time like 10m, 2h, 3d)
- `/warn` - Warn users (auto-ban after 3 warnings)
- `/kick` - Kick users from group
- `/purge` - Delete multiple messages

### 📝 Filters & Notes
- Create auto-responses to keywords
- Save important information as notes
- Manage via inline keyboards
- Inline query support for quick note access

### 🎨 Theme System
Choose from 8 beautiful color themes:
- 🔵 **Default** - Classic blue theme
- 🌊 **Ocean** - Sea-inspired colors
- 🌲 **Forest** - Nature greens
- 🌅 **Sunset** - Warm oranges
- 💜 **Cyber** - Neon cyberpunk
- ⭐ **Galaxy** - Space themed
- 🔥 **Fire** - Hot reds
- ❄️ **Ice** - Cool blues

### 🔧 Permissions Control
- Granular control over member permissions
- Lock/unlock chat with one command
- Toggle individual permissions via inline panel

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Bot
Edit `src/configs/settings.py` or set environment variables:
```bash
export BOT_TOKEN="your_bot_token_from_botfather"
export DATABASE_URL="sqlite+aiosqlite:///bot_database.db"
export ADMINS="123456789,987654321"
```

### 3. Run the Bot
```bash
python src/bot.py
```

## 📖 Commands

| Command | Description |
|---------|-------------|
| `/settings` | Open interactive settings panel |
| `/lock` | Lock chat |
| `/unlock` | Unlock chat |
| `/ban` | Ban a user |
| `/mute` | Mute a user |
| `/warn` | Warn a user |
| `/kick` | Kick a user |
| `/theme` | Change button theme |

## 🏗️ Project Structure

```
src/
├── bot.py              # Main entry point
├── configs/settings.py # Configuration
├── handlers/           # All command handlers
├── models/database.py  # SQLAlchemy models
└── utils/              # Helpers and keyboards
```

## 🎨 Custom Themes

The bot features a unique emoji-based theming system with 8 themes:
- default, ocean, forest, sunset, cyber, galaxy, fire, ice

## 📄 License

MIT License

---

Made with ❤️ for Telegram communities
