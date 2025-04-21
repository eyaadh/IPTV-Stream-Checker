import socket
import time
from urllib.parse import urlparse
import logging
import requests
import json
from apscheduler.schedulers.background import BackgroundScheduler

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration from JSON
try:
    with open('config.json', 'r') as f:
        config = json.load(f)

    TELEGRAM_BOT_TOKEN = config['telegram']['bot_token']
    TELEGRAM_CHAT_ID = config['telegram']['chat_id']
    TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    udp_streams = config['streams']['udp']
    if not udp_streams:
        logger.error("No UDP streams found in configuration")
        exit(1)
except (KeyError, FileNotFoundError, json.JSONDecodeError) as e:
    logger.error(f"Failed to load configuration: {e}")
    exit(1)


def send_telegram_message(message):
    try:
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message
        }
        response = requests.post(TELEGRAM_API_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Telegram message sent: {message}")
    except requests.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")


def parse_udp_url(udp_url):
    try:
        if udp_url.startswith("udp://@"):
            udp_url = udp_url.replace("udp://@", "udp://", 1)
        parsed = urlparse(udp_url)
        if parsed.scheme != 'udp':
            raise ValueError(f"Invalid scheme for {udp_url}. Expected 'udp'.")
        host = parsed.hostname
        port = parsed.port
        if not host or not port:
            raise ValueError(f"Invalid UDP URL format: {udp_url}")
        return host, port
    except Exception as e:
        logger.error(f"Failed to parse UDP URL {udp_url}: {e}")
        return None, None


def check_udp_stream(host, port, timeout=10, require_data=False):
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(timeout)

        is_multicast = host.startswith("224.") or host.startswith("225.") or \
                       host.startswith("226.") or host.startswith("227.") or \
                       host.startswith("228.") or host.startswith("229.") or \
                       host.startswith("230.") or host.startswith("231.") or \
                       host.startswith("232.") or host.startswith("233.") or \
                       host.startswith("234.") or host.startswith("235.") or \
                       host.startswith("236.") or host.startswith("237.") or \
                       host.startswith("238.") or host.startswith("239.")

        logger.debug(f"Checking {host}:{port} (Multicast: {is_multicast})")

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', port))

        if is_multicast:
            import struct
            mreq = struct.pack("4sl", socket.inet_aton(host), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            logger.debug(f"Joined multicast group {host}")

        if require_data:
            try:
                logger.debug(f"Waiting for data from {host}:{port}")
                data, addr = sock.recvfrom(4096)
                if data:
                    logger.info(f"Stream {host}:{port} is ACTIVE (received {len(data)} bytes from {addr})")
                    return True
            except socket.timeout:
                logger.warning(f"Stream {host}:{port} is INACTIVE (no data received within {timeout}s)")
                return False
        else:
            logger.info(f"Stream {host}:{port} is ACTIVE (binding succeeded)")
            return True

    except Exception as e:
        logger.error(f"Error checking stream {host}:{port}: {e}")
        return False
    finally:
        if sock:
            sock.close()
            logger.debug(f"Closed socket for {host}:{port}")


def check_channels(streams, timeout=10, retry_attempts=2, retry_delay=2, require_data=False):
    results = {}
    down_streams = []

    for stream in streams:
        name = stream.get("name")
        url = stream.get("url")

        if not name or not url:
            logger.error(f"Missing name or url in stream: {stream}")
            continue

        host, port = parse_udp_url(url)
        if not host or not port:
            results[name] = {'status': 'INVALID', 'error': 'Invalid URL'}
            down_streams.append((name, 'Invalid URL'))
            continue

        for attempt in range(retry_attempts):
            logger.info(f"Checking {name} ({url}) - Attempt {attempt + 1}/{retry_attempts}")
            if check_udp_stream(host, port, timeout, require_data):
                results[name] = {'status': 'ACTIVE', 'error': None}
                break
            else:
                results[name] = {'status': 'INACTIVE', 'error': 'No response or timeout'}
                if attempt < retry_attempts - 1:
                    logger.info(f"Retrying {name} after {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    down_streams.append((name, 'No response or timeout'))

    if down_streams:
        message = "🚨 IPTV Stream Alert 🚨\nThe following channels are DOWN:\n"
        for name, error in down_streams:
            message += f"- {name}: {error}\n"
        send_telegram_message(message)

    return results


def scheduled_task():
    logger.info("Starting scheduled UDP stream check...")
    results = check_channels(udp_streams, timeout=10, retry_attempts=2, retry_delay=2, require_data=True)

    logger.info("\nChannel Status Report:")
    logger.info("-" * 50)
    for name, info in results.items():
        status = info['status']
        error = info['error'] if info['error'] else 'None'
        logger.info(f"Channel: {name}\nStatus: {status}\nError: {error}\n")


def main():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_task, 'interval', hours=1)

    logger.info("Starting scheduler and running first check immediately...")
    scheduled_task()  # Run immediately on startup
    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
