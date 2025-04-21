# 🔍 IPTV UDP Stream Checker with Telegram Alerts

This Python script monitors a list of UDP streams (unicast or multicast) and sends a Telegram alert if any stream becomes inactive or unreachable.

Perfect for IPTV providers, network admins, or anyone relying on uninterrupted UDP stream delivery.

---

## 🚀 Features

- ✅ Supports both multicast and unicast UDP streams.
- ✅ Retries failed stream checks before declaring them down.
- ✅ Optional requirement for receiving actual data (for more accurate checks).
- ✅ Sends real-time alerts to Telegram when streams go down.
- ✅ Uses a scheduler to run periodic checks (default: **every 1 hour**).
- ✅ Detailed logs for monitoring, alerts, and debugging.

---

## 📦 Requirements

- Python 3.6+
- Install dependencies using:

```bash
pip install -r requirements.txt
```

Contents of `requirements.txt`:
```txt
requests==2.32.3
apscheduler==3.10.4
```

---

## ⚙️ Configuration

Create a file named `config.json` in the same directory:

```json
{
  "telegram": {
    "bot_token": "your_telegram_bot_token_here",
    "chat_id": "your_telegram_chat_id_here"
  },
  "streams": {
    "udp": [
      {
        "name": "Channel 1",
        "url": "udp://239.1.1.1:1234"
      },
      {
        "name": "Channel 2",
        "url": "udp://239.1.1.2:5678"
      }
    ]
  }
}
```

- Replace `bot_token` and `chat_id` with your Telegram bot credentials.
- Add as many UDP streams as needed, each with a descriptive `name` and valid `url`.

---

## 📡 How It Works

1. Loads UDP streams and Telegram bot settings from `config.json`.
2. Parses each stream's address and checks for availability.
3. If multicast, joins the group before checking.
4. Optionally listens for real UDP traffic (`require_data=True`).
5. Retries failed streams before marking them as down.
6. Sends a Telegram alert if any streams are unreachable.

---

## 🛠️ Usage

Run the script with:

```bash
python main.py
```

What it does:
- Immediately runs a stream check.
- Starts a background scheduler that checks **every hour**.
- Keeps running until terminated manually.

---

## 🔄 Customization

You can adjust the stream-check behavior by modifying the parameters inside the `scheduled_task()` function:

```python
check_channels(
    udp_streams,
    timeout=10,             # Timeout per attempt (in seconds)
    retry_attempts=2,       # Number of retries before failure
    retry_delay=2,          # Delay between retries (in seconds)
    require_data=True       # Set to True to require actual packet reception
)
```

---

## 📬 Telegram Bot Setup

1. Message [@BotFather](https://t.me/BotFather)
2. Create a new bot: `/newbot`
3. Copy the generated `bot_token`
4. To find your chat ID:
   - Start a conversation with your bot.
   - Visit:  
     ```
     https://api.telegram.org/bot<your_bot_token>/getUpdates
     ```
   - Look for `"chat":{"id":...}` in the JSON response.

---

## 📝 Example Telegram Alert

```
🚨 IPTV Stream Alert 🚨
The following channels are DOWN:
- Channel 1: No response or timeout
- Channel 2: Invalid URL
```

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 👨‍💻 Author

Built with ❤️ by **eyaadh**  
📧 Email: eyaadh@eyaadh.net  
💬 Telegram: [@eyaadh](https://t.me/eyaadh)