"""
HIOKI SIMPLE RECEIVER
=====================
Runs on the SERVER where the Hioki BT3562A is physically connected.
Listens on TCP port 5000 for measurement data sent by the device.

Supported data formats from Hioki:
  JSON   : {"voltage": 12.5, "resistance": 250.5}
  CSV    : 12.5,250.5
  KV     : V:12.5,R:250.5   or   voltage:12.5,resistance:250.5

Start (server):
  python hioki_simple_receiver.py              # default port 5000
  python hioki_simple_receiver.py --port 5001  # custom port
  python hioki_simple_receiver.py --host 0.0.0.0 --port 5000

Runs forever; press Ctrl-C to stop.
"""

import socket
import sqlite3
import json
import logging
import argparse
import threading
import re
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_HOST = "0.0.0.0"     # accept from any interface (Hioki on LAN)
DEFAULT_PORT = 5000
DB_PATH = "hioki_measurements.db"
LOG_DIR = "logs"
MAX_VOLTAGE = 30.0
MAX_RESISTANCE = 10_000.0

# ---------------------------------------------------------------------------
# Logging  (console + rotating file)
# ---------------------------------------------------------------------------

Path(LOG_DIR).mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"{LOG_DIR}/hioki_receiver.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("HiokiReceiver")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def init_db(db_path: str = DB_PATH) -> None:
    """Create tables if they do not already exist."""
    with sqlite3.connect(db_path) as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS measurements (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT UNIQUE NOT NULL,
                voltage     REAL NOT NULL,
                resistance  REAL NOT NULL,
                device_name TEXT DEFAULT "Hioki BT3562A",
                notes       TEXT DEFAULT "",
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS daily_stats (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                date           TEXT UNIQUE NOT NULL,
                total_scans    INTEGER DEFAULT 0,
                avg_voltage    REAL,
                avg_resistance REAL,
                min_voltage    REAL,
                max_voltage    REAL,
                min_resistance REAL,
                max_resistance REAL,
                updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.commit()
    logger.info(f"Database ready  →  {db_path}")


def save_measurement(
    voltage: float,
    resistance: float,
    device_name: str = "Hioki BT3562A",
    notes: str = "",
    db_path: str = DB_PATH,
) -> bool:
    """
    Persist one validated measurement.

    Returns True on success, False on any error.
    """
    timestamp = datetime.now().isoformat()
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                '''
                INSERT OR IGNORE INTO measurements
                    (timestamp, voltage, resistance, device_name, notes)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (timestamp, voltage, resistance, device_name, notes),
            )
            conn.commit()
        logger.info(f"Saved  →  {voltage:.4f} V  |  {resistance:.4f} Ω")
        return True
    except Exception as exc:
        logger.error(f"DB write failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Data parsers
# ---------------------------------------------------------------------------

def parse_message(raw: str) -> tuple[float, float] | None:
    """
    Extract (voltage, resistance) from raw text.

    Tries, in order:
      1. JSON  {"voltage": ..., "resistance": ...}
      2. Key-value  V:X,R:Y  or  voltage:X,resistance:Y
      3. Plain CSV  X,Y

    Returns (voltage, resistance) or None if all parsers fail.
    """
    text = raw.strip()

    # --- JSON ---
    if text.startswith("{"):
        try:
            data = json.loads(text)
            v = float(data.get("voltage") or data.get("V") or data.get("v") or 0)
            r = float(data.get("resistance") or data.get("R") or data.get("r") or 0)
            return v, r
        except Exception:
            pass

    # --- Key:Value ---
    kv = re.search(
        r"(?:voltage|v)\s*[:=]\s*([\d.]+).*?(?:resistance|r)\s*[:=]\s*([\d.]+)",
        text,
        re.IGNORECASE,
    )
    if kv:
        try:
            return float(kv.group(1)), float(kv.group(2))
        except ValueError:
            pass

    # --- Plain CSV ---
    parts = text.split(",")
    if len(parts) >= 2:
        try:
            return float(parts[0].strip()), float(parts[1].strip())
        except ValueError:
            pass

    return None


def validate(voltage: float, resistance: float) -> bool:
    """Return True only if both values are within physical limits."""
    if not (0.0 <= voltage <= MAX_VOLTAGE):
        logger.warning(f"Voltage out of range: {voltage} V  (0–{MAX_VOLTAGE})")
        return False
    if not (0.0 <= resistance <= MAX_RESISTANCE):
        logger.warning(f"Resistance out of range: {resistance} Ω  (0–{MAX_RESISTANCE})")
        return False
    return True


# ---------------------------------------------------------------------------
# Per-connection handler (runs in its own thread)
# ---------------------------------------------------------------------------

def handle_client(client_sock: socket.socket, addr: tuple, db_path: str) -> None:
    """Read one message, parse, validate, persist, and reply."""
    logger.info(f"Connection from {addr[0]}:{addr[1]}")
    try:
        with client_sock:
            client_sock.settimeout(10.0)
            raw = client_sock.recv(4096).decode("utf-8", errors="replace")

            if not raw.strip():
                logger.warning(f"Empty payload from {addr}")
                client_sock.sendall(b"ERROR:empty_payload\n")
                return

            logger.debug(f"Raw: {raw!r}")
            result = parse_message(raw)

            if result is None:
                logger.warning(f"Unrecognised format from {addr}: {raw!r}")
                client_sock.sendall(b"ERROR:parse_failed\n")
                return

            voltage, resistance = result

            if not validate(voltage, resistance):
                client_sock.sendall(b"ERROR:validation_failed\n")
                return

            if save_measurement(voltage, resistance, db_path=db_path):
                client_sock.sendall(b"OK\n")
            else:
                client_sock.sendall(b"ERROR:db_write_failed\n")

    except socket.timeout:
        logger.warning(f"Timeout from {addr}")
    except Exception as exc:
        logger.error(f"Handler error ({addr}): {exc}")


# ---------------------------------------------------------------------------
# Main server loop
# ---------------------------------------------------------------------------

def run_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    db_path: str = DB_PATH,
) -> None:
    """Bind, listen, and dispatch each connection to a daemon thread."""
    init_db(db_path)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(10)

        logger.info("=" * 60)
        logger.info("  Hioki Simple Receiver  —  STARTED")
        logger.info(f"  Listening  : {host}:{port}")
        logger.info(f"  Database   : {db_path}")
        logger.info(f"  Voltage    : 0 – {MAX_VOLTAGE} V")
        logger.info(f"  Resistance : 0 – {MAX_RESISTANCE} Ω")
        logger.info("  Ctrl-C to stop")
        logger.info("=" * 60)

        while True:
            try:
                client_sock, addr = srv.accept()
                threading.Thread(
                    target=handle_client,
                    args=(client_sock, addr, db_path),
                    daemon=True,
                ).start()
            except KeyboardInterrupt:
                logger.info("Receiver stopped by user (Ctrl-C).")
                break
            except Exception as exc:
                logger.error(f"Accept error: {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Hioki Simple TCP Receiver")
    ap.add_argument("--host", default=DEFAULT_HOST,
                    help=f"Bind address (default: {DEFAULT_HOST})")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT,
                    help=f"Bind port (default: {DEFAULT_PORT})")
    ap.add_argument("--db", default=DB_PATH,
                    help=f"SQLite DB path (default: {DB_PATH})")
    args = ap.parse_args()

    run_server(host=args.host, port=args.port, db_path=args.db)
