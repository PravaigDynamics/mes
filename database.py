"""
Database layer for Battery Pack MES - FIXED VERSION
Handles concurrent data writes safely
Supports both PostgreSQL (production) and SQLite (local testing)
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Database connection handling
_connection_pool = None


def get_database_url():
    """Get database URL from environment or use local SQLite fallback"""
    return os.getenv('DATABASE_URL', 'sqlite:///battery_mes.db')


def get_connection():
    """Get database connection (PostgreSQL or SQLite)"""
    db_url = get_database_url()

    if db_url.startswith('postgres'):
        # PostgreSQL
        import psycopg2
        return psycopg2.connect(db_url)
    else:
        # SQLite
        import sqlite3
        conn = sqlite3.connect('battery_mes.db')
        conn.row_factory = sqlite3.Row
        return conn


def release_connection(conn):
    """Close connection"""
    conn.close()


def init_database():
    """Create database tables if they don't exist"""
    conn = get_connection()
    db_url = get_database_url()
    is_postgres = db_url.startswith('postgres')

    try:
        cur = conn.cursor()

        # Battery packs table
        if is_postgres:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS battery_packs (
                    id SERIAL PRIMARY KEY,
                    pack_id VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50)
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS battery_packs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pack_id VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50)
                )
            """)

        # QC checks table
        if is_postgres:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS qc_checks (
                    id SERIAL PRIMARY KEY,
                    pack_id VARCHAR(100) NOT NULL,
                    process_name VARCHAR(100) NOT NULL,
                    check_name TEXT,
                    module_x VARCHAR(20),
                    module_y VARCHAR(20),
                    technician_name VARCHAR(100),
                    qc_name VARCHAR(100),
                    remarks TEXT,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS qc_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pack_id VARCHAR(100) NOT NULL,
                    process_name VARCHAR(100) NOT NULL,
                    check_name TEXT,
                    module_x VARCHAR(20),
                    module_y VARCHAR(20),
                    technician_name VARCHAR(100),
                    qc_name VARCHAR(100),
                    remarks TEXT,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE
                )
            """)

        # Create indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_qc_pack_id ON qc_checks(pack_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_qc_pack_process ON qc_checks(pack_id, process_name)
        """)

        conn.commit()
        logger.info(f"Database initialized ({'PostgreSQL' if is_postgres else 'SQLite'})")

    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def save_battery_pack(pack_id: str) -> bool:
    """Create or update battery pack record"""
    conn = get_connection()
    db_url = get_database_url()
    is_postgres = db_url.startswith('postgres')

    try:
        cur = conn.cursor()
        timestamp = datetime.now()

        if is_postgres:
            cur.execute("""
                INSERT INTO battery_packs (pack_id, created_at, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (pack_id)
                DO UPDATE SET updated_at = %s
            """, (pack_id, timestamp, timestamp, timestamp))
        else:
            cur.execute("""
                INSERT OR REPLACE INTO battery_packs (pack_id, created_at, updated_at)
                VALUES (?, ?, ?)
            """, (pack_id, timestamp, timestamp))

        conn.commit()
        return True

    except Exception as e:
        logger.error(f"Error saving battery pack {pack_id}: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)


def save_qc_checks(pack_id: str, process_name: str, technician_name: str,
                   qc_name: str, remarks: str, checks: List[Dict]) -> bool:
    """Save QC check data to database"""
    conn = get_connection()
    db_url = get_database_url()
    is_postgres = db_url.startswith('postgres')

    try:
        cur = conn.cursor()

        # Ensure battery pack exists
        save_battery_pack(pack_id)

        # Delete existing data for this pack + process
        if is_postgres:
            cur.execute("DELETE FROM qc_checks WHERE pack_id = %s AND process_name = %s",
                       (pack_id, process_name))
        else:
            cur.execute("DELETE FROM qc_checks WHERE pack_id = ? AND process_name = ?",
                       (pack_id, process_name))

        # Insert new check data
        timestamp = datetime.now()

        for check in checks:
            if is_postgres:
                cur.execute("""
                    INSERT INTO qc_checks
                    (pack_id, process_name, check_name, module_x, module_y,
                     technician_name, qc_name, remarks, start_date, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (pack_id, process_name, check.get('check_name', ''),
                      check.get('module_x', ''), check.get('module_y', ''),
                      technician_name, qc_name, remarks,
                      timestamp, timestamp, timestamp))
            else:
                cur.execute("""
                    INSERT INTO qc_checks
                    (pack_id, process_name, check_name, module_x, module_y,
                     technician_name, qc_name, remarks, start_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (pack_id, process_name, check.get('check_name', ''),
                      check.get('module_x', ''), check.get('module_y', ''),
                      technician_name, qc_name, remarks,
                      timestamp, timestamp, timestamp))

        conn.commit()
        logger.info(f"Saved {len(checks)} QC checks for {pack_id} - {process_name}")
        return True

    except Exception as e:
        logger.error(f"Error saving QC checks: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)


def update_process_completion(pack_id: str, process_name: str) -> bool:
    """Update end_date for a process (when "Complete Process" is clicked)"""
    conn = get_connection()
    db_url = get_database_url()
    is_postgres = db_url.startswith('postgres')

    try:
        cur = conn.cursor()
        timestamp = datetime.now()

        if is_postgres:
            cur.execute("""
                UPDATE qc_checks SET end_date = %s, updated_at = %s
                WHERE pack_id = %s AND process_name = %s
            """, (timestamp, timestamp, pack_id, process_name))
        else:
            cur.execute("""
                UPDATE qc_checks SET end_date = ?, updated_at = ?
                WHERE pack_id = ? AND process_name = ?
            """, (timestamp, timestamp, pack_id, process_name))

        conn.commit()
        logger.info(f"Completed process {process_name} for {pack_id}")
        return True

    except Exception as e:
        logger.error(f"Error completing process: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)


def get_qc_checks(pack_id: str, process_name: str = None) -> List[Dict]:
    """Get QC check data from database"""
    conn = get_connection()
    db_url = get_database_url()
    is_postgres = db_url.startswith('postgres')

    try:
        cur = conn.cursor()

        if process_name:
            if is_postgres:
                cur.execute("""
                    SELECT * FROM qc_checks
                    WHERE pack_id = %s AND process_name = %s
                    ORDER BY created_at ASC
                """, (pack_id, process_name))
            else:
                cur.execute("""
                    SELECT * FROM qc_checks
                    WHERE pack_id = ? AND process_name = ?
                    ORDER BY created_at ASC
                """, (pack_id, process_name))
        else:
            if is_postgres:
                cur.execute("""
                    SELECT * FROM qc_checks
                    WHERE pack_id = %s
                    ORDER BY process_name, created_at ASC
                """, (pack_id,))
            else:
                cur.execute("""
                    SELECT * FROM qc_checks
                    WHERE pack_id = ?
                    ORDER BY process_name, created_at ASC
                """, (pack_id,))

        rows = cur.fetchall()

        # Convert rows to dicts (works for both PostgreSQL and SQLite)
        result = []
        for row in rows:
            if is_postgres:
                # PostgreSQL with RealDictCursor
                from psycopg2.extras import RealDictCursor
                result.append(dict(row))
            else:
                # SQLite with Row factory
                result.append(dict(row))

        return result

    except Exception as e:
        logger.error(f"Error fetching QC checks: {e}")
        return []
    finally:
        release_connection(conn)


def get_all_battery_packs() -> List[str]:
    """Get list of all battery pack IDs"""
    conn = get_connection()

    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT pack_id FROM battery_packs ORDER BY pack_id")
        rows = cur.fetchall()
        return [row[0] for row in rows]

    except Exception as e:
        logger.error(f"Error fetching battery packs: {e}")
        return []
    finally:
        release_connection(conn)


def get_dashboard_status() -> List[Dict]:
    """
    Get dashboard status for all battery packs with process completion
    Returns list of dicts with pack_id and process status
    """
    conn = get_connection()

    try:
        cur = conn.cursor()

        # Get all battery packs and their processes
        cur.execute("""
            SELECT DISTINCT pack_id, process_name
            FROM qc_checks
            ORDER BY pack_id, process_name
        """)
        rows = cur.fetchall()

        # Group by pack_id
        pack_statuses = {}
        for pack_id, process_name in rows:
            if pack_id not in pack_statuses:
                pack_statuses[pack_id] = {}
            pack_statuses[pack_id][process_name] = "QC OK"  # If data exists, mark as OK

        # Convert to list format
        result = []
        for pack_id, processes in pack_statuses.items():
            result.append({
                'pack_id': pack_id,
                'processes': processes
            })

        return result

    except Exception as e:
        logger.error(f"Error getting dashboard status: {e}")
        return []
    finally:
        release_connection(conn)


def check_process_status(pack_id: str, process_name: str) -> Dict:
    """Check if process has data and completion status"""
    result = {
        'exists': False,
        'started': False,
        'completed': False,
        'process_type': None
    }

    try:
        from app_unified_db import PROCESS_ROW_MAPPING
        process_info = PROCESS_ROW_MAPPING.get(process_name)
        if not process_info:
            return result

        result['process_type'] = process_info['type']
        checks = get_qc_checks(pack_id, process_name)

        if checks:
            result['exists'] = True
            result['started'] = any(check.get('start_date') for check in checks)
            result['completed'] = any(check.get('end_date') for check in checks)

        return result

    except Exception as e:
        logger.error(f"Error checking process status: {e}")
        return result


def battery_pack_exists(pack_id: str) -> bool:
    """Check if battery pack exists in database"""
    conn = get_connection()
    db_url = get_database_url()
    is_postgres = db_url.startswith('postgres')

    try:
        cur = conn.cursor()

        if is_postgres:
            cur.execute("SELECT COUNT(*) FROM battery_packs WHERE pack_id = %s", (pack_id,))
        else:
            cur.execute("SELECT COUNT(*) FROM battery_packs WHERE pack_id = ?", (pack_id,))

        count = cur.fetchone()[0]
        return count > 0

    except Exception as e:
        logger.error(f"Error checking battery pack existence: {e}")
        return False
    finally:
        release_connection(conn)
