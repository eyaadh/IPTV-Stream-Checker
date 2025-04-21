import socket
import time
from urllib.parse import urlparse
import logging
import configparser
import requests
from apscheduler.schedulers.background import BackgroundScheduler

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration from .config file
config = configparser.ConfigParser()
config.read('config.ini')

# Telegram configuration
try:
    TELEGRAM_BOT_TOKEN = config['Telegram']['bot_token']
    TELEGRAM_CHAT_ID = config['Telegram']['chat_id']
    TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
except KeyError as e:
    logger.error(f"Missing configuration key: {e}")
    exit(1)

# Load UDP streams from config
try:
    udp_streams = [stream.strip() for stream in config['Streams']['udp_streams'].split(',')]
    if not udp_streams:
        logger.error("No UDP streams found in configuration")
        exit(1)
except KeyError as e:
    logger.error(f"Missing configuration key: {e}")
    exit(1)

def send_telegram_message(message):
    """Send a message via Telegram using HTTP API."""
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
    """Parse a UDP URL to extract host and port."""
    try:
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
    """Check if a UDP stream is active by receiving data, especially useful for multicast."""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(timeout)

        is_multicast = host.startswith('224.') or host.startswith('225.') or host.startswith('226.') or \
                       host.startswith('227.') or host.startswith('228.') or host.startswith('229.') or \
                       host.startswith('230.') or host.startswith('231.') or host.startswith('232.') or \
                       host.startswith('233.') or host.startswith('234.') or host.startswith('235.') or \
                       host.startswith('236.') or host.startswith('237.') or host.startswith('238.') or \
                       host.startswith('239.')

        logger.debug(f"Checking {host}:{port} (Multicast: {is_multicast})")

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', port))  # Bind to all interfaces on the specified port

        if is_multicast:
            import struct
            mreq = struct.pack("4sl", socket.inet_aton(host), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            logger.debug(f"Joined multicast group {host}")

        if require_data:
            try:
                logger.debug(f"Waiting for data from {host}:{port}")
                data, addr = sock.recvfrom(4096)  # wait for actual data
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

    """Check if a UDP stream is active by attempting to bind and optionally receive data."""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        is_multicast = host.startswith('2')  # Multicast: 224.0.0.0 to 239.255.255.255
        logger.debug(f"Checking {host}:{port} (Multicast: {is_multicast})")
        
        if is_multicast:
            # Enable reuse of address for multicast
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to the port
            sock.bind(('', port))
            logger.debug(f"Bound to port {port} for multicast")
            # Join multicast group
            import struct
            mreq = struct.pack('4sl', socket.inet_aton(host), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            logger.debug(f"Joined multicast group {host}")
        else:
            # For unicast, bind to any address
            sock.bind(('', port))
            logger.debug(f"Bound to port {port} for unicast")
        
        if require_data:
            # Optionally send a dummy packet and try to receive data
            sock.sendto(b'', (host, port))
            logger.debug(f"Sent dummy packet to {host}:{port}")
            data, addr = sock.recvfrom(1024)
            logger.debug(f"Received data from {addr}: {len(data)} bytes")
            if data:
                logger.info(f"Stream {host}:{port} is ACTIVE (data received)")
                return True
            else:
                logger.warning(f"Stream {host}:{port} is INACTIVE (no data received)")
                return False
        else:
            # If not requiring data, consider the stream active if binding and multicast joining succeeded
            logger.info(f"Stream {host}:{port} is ACTIVE (binding successful)")
            return True
            
    except socket.timeout:
        logger.warning(f"Stream {host}:{port} is INACTIVE (timeout)")
        return False
    except socket.error as e:
        logger.error(f"Socket error for stream {host}:{port}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error checking stream {host}:{port}: {e}")
        return False
    finally:
        if sock:
            sock.close()
            logger.debug(f"Closed socket for {host}:{port}")

def check_channels(udp_urls, timeout=10, retry_attempts=2, retry_delay=2, require_data=False):
    """Check the status of a list of UDP streams and notify via Telegram if any are down."""
    results = {}
    down_streams = []
    
    for url in udp_urls:
        host, port = parse_udp_url(url)
        if not host or not port:
            results[url] = {'status': 'INVALID', 'error': 'Invalid URL'}
            down_streams.append((url, 'Invalid URL'))
            continue
        
        for attempt in range(retry_attempts):
            logger.info(f"Checking {url} (Attempt {attempt + 1}/{retry_attempts})")
            if check_udp_stream(host, port, timeout, require_data):
                results[url] = {'status': 'ACTIVE', 'error': None}
                break
            else:
                results[url] = {'status': 'INACTIVE', 'error': 'No response or timeout'}
                if attempt < retry_attempts - 1:
                    logger.info(f"Retrying {url} after {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    down_streams.append((url, 'No response or timeout'))
    
    # Send Telegram notification if any streams are down
    if down_streams:
        message = "🚨 IPTV Stream Alert 🚨\nThe following streams are DOWN:\n"
        for url, error in down_streams:
            message += f"- {url}: {error}\n"
        send_telegram_message(message)
    
    return results

def scheduled_task():
    """Task to run periodically to check UDP streams."""
    logger.info("Starting scheduled UDP stream check...")
    results = check_channels(udp_streams, timeout=10, retry_attempts=2, retry_delay=2, require_data=True)
    
    # Log results
    logger.info("\nChannel Status Report:")
    logger.info("-" * 50)
    for url, info in results.items():
        status = info['status']
        error = info['error'] if info['error'] else 'None'
        logger.info(f"Channel: {url}\nStatus: {status}\nError: {error}\n")

def main():
    """Set up the scheduler and start checking streams."""
    # Initialize scheduler
    scheduler = BackgroundScheduler()
    
    # Schedule the task to run every 5 minutes
    scheduler.add_job(scheduled_task, 'interval', seconds=10)
    
    # Start the scheduler
    logger.info("Starting scheduler...")
    scheduler.start()
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        # Shut down the scheduler gracefully
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()

if __name__ == "__main__":
    main()