# 🔍 IPTV UDP Stream Checker with Telegram Alerts

This Python script monitors a list of UDP streams (unicast or multicast) and sends a Telegram notification if any streams are inactive or unreachable.

Ideal for IPTV providers, network admins, or systems where reliable UDP streams are critical.

---

## 🚀 Features

- ✅ Monitors multicast or unicast UDP streams.
- ✅ Automatically retries failed checks.
- ✅ Optional check for actual incoming data (recommended for multicast).
- ✅ Sends alerts via Telegram bot when streams are down.
- ✅ Scheduled to run periodically (default: every 5 minutes).
- ✅ Detailed logs for monitoring and debugging.

---

## 📦 Requirements

- Python 3.6+
- Required Python packages (install with pip):

```bash
pip install requests apscheduler
```

---

## ⚙️ Configuration

Create a file named `config.ini` in the same directory as the script:

```ini
[Telegram]
bot_token = your_telegram_bot_token_here
chat_id = your_chat_id_here

[Streams]
udp_streams = udp://239.1.1.1:1234,udp://239.1.1.2:5678
```

- Replace `bot_token` and `chat_id` with your Telegram Bot credentials.
- Add one or more comma-separated UDP stream URLs (must use the format `udp://host:port`).

---

## 📡 How It Works

1. Parses each UDP stream from the config.
2. Joins multicast groups or binds to unicast addresses.
3. Optionally listens for actual incoming data.
4. Retries a few times before marking a stream as down.
5. Sends a detailed Telegram message if any streams are unreachable.

---

## 🛠️ Usage

Simply run the script:

```bash
python main.py
```

It will:
- Start a background scheduler
- Run checks every 5 minutes
- Keep the process alive

---

## 🔄 Customization

You can tweak these inside the script:

```python
# Inside scheduled_task()
check_channels(
    udp_streams,
    timeout=10,             # Wait time in seconds for data (per attempt)
    retry_attempts=2,       # Number of retries before declaring failure
    retry_delay=2,          # Seconds to wait between retries
    require_data=True       # Set to True to require actual UDP packets
)
```

---

## 📬 Telegram Bot Setup

1. Start a chat with [BotFather](https://t.me/BotFather)
2. Create a new bot: `/newbot`
3. Get the `bot_token`
4. Get your `chat_id`:
   - Start a chat with your bot.
   - Visit: `https://api.telegram.org/bot<your_token>/getUpdates`
   - Find your chat ID in the response.

---

## 📝 Example Telegram Alert

```
🚨 IPTV Stream Alert 🚨
The following streams are DOWN:
- udp://239.1.1.1:1234: No response or timeout
```

---

## 📄 License

MIT License — free to use, modify, and share.

---

## 👨‍💻 Author

Built with ❤️ by eyaadh.\
Contact: eyaadh@eyaadh.net | Telegram: @eyaadh