"""
Database layer for Battery Pack MES - CONCURRENT ACCESS VERSION
Handles concurrent data writes safely with retry logic
Supports both PostgreSQL (production) and SQLite (local testing)
Enhanced for multiple simultaneous users
"""

import os
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Get the directory where this script is located (for absolute database path)
SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / 'battery_mes.db'

# Database connection handling
_connection_pool = None

# Concurrent access configuration
MAX_RETRIES = 10
RETRY_DELAY = 0.1  # 100ms initial delay
MAX_RETRY_DELAY = 2.0  # 2 seconds max delay


def get_database_url():
    """Get database URL from environment or use local SQLite fallback"""
    return os.getenv('DATABASE_URL', 'sqlite:///battery_mes.db')


def get_connection():
    """Get database connection (PostgreSQL or SQLite) with concurrent access support"""
    db_url = get_database_url()

    if db_url.startswith('postgres'):
        # PostgreSQL
        import psycopg2
        return psycopg2.connect(db_url)
    else:
        # SQLite with optimizations for concurrent access
        import sqlite3

        # Increased timeout for concurrent writes (30 seconds)
        # Use absolute path to ensure correct database file regardless of working directory
        conn = sqlite3.connect(str(DB_PATH), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrent access
        # WAL allows multiple readers and one writer at the same time
        conn.execute('PRAGMA journal_mode=WAL')

        # Set synchronous mode to NORMAL for better performance while maintaining safety
        conn.execute('PRAGMA synchronous=NORMAL')

        # Enable auto-checkpoint at 1000 pages
        conn.execute('PRAGMA wal_autocheckpoint=1000')

        # Increase cache size for better performance (10MB)
        conn.execute('PRAGMA cache_size=-10000')

        return conn


def release_connection(conn):
    """Close connection"""
    conn.close()


def retry_on_db_lock(func):
    """
    Decorator to retry database operations on lock/busy errors
    Essential for concurrent access with SQLite
    """
    def wrapper(*args, **kwargs):
        import sqlite3

        delay = RETRY_DELAY
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)

            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()

                # Retry only on database locked/busy errors
                if 'locked' in error_msg or 'busy' in error_msg:
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"Database locked on attempt {attempt + 1}, retrying in {delay}s...")
                        time.sleep(delay)

                        # Exponential backoff with jitter
                        delay = min(delay * 2, MAX_RETRY_DELAY)
                        continue
                    else:
                        logger.error(f"Database locked after {MAX_RETRIES} attempts")
                        raise

                # Re-raise non-lock errors immediately
                raise

            except Exception as e:
                # PostgreSQL or other errors - check if it's a serialization error
                error_msg = str(e).lower()
                if 'serialization' in error_msg or 'deadlock' in error_msg:
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"Serialization error on attempt {attempt + 1}, retrying...")
                        time.sleep(delay)
                        delay = min(delay * 2, MAX_RETRY_DELAY)
                        continue

                # Re-raise all other errors
                raise

        # Should never reach here, but just in case
        raise Exception(f"Failed after {MAX_RETRIES} retries")

    return wrapper


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


@retry_on_db_lock
def save_battery_pack(pack_id: str) -> bool:
    """Create or update battery pack record with retry on lock"""
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
        logger.debug(f"Saved battery pack: {pack_id}")
        return True

    except Exception as e:
        logger.error(f"Error saving battery pack {pack_id}: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)


@retry_on_db_lock
def save_qc_checks(pack_id: str, process_name: str, technician_name: str,
                   qc_name: str, remarks: str, checks: List[Dict]) -> bool:
    """
    Save QC check data to database with retry on lock (handles concurrent writes)
    IMPORTANT: This function MERGES data instead of overwriting
    - If Employee X saves Module X data, it updates only Module X fields
    - If Employee B saves Module Y data, it updates only Module Y fields
    - Both modules' data are preserved!
    """
    conn = get_connection()
    db_url = get_database_url()
    is_postgres = db_url.startswith('postgres')

    try:
        cur = conn.cursor()

        # Ensure battery pack exists
        save_battery_pack(pack_id)

        # Use immediate transaction for write lock (SQLite)
        if not is_postgres:
            conn.isolation_level = 'IMMEDIATE'

        timestamp = datetime.now()

        # MERGE strategy: Update or Insert each check
        for check in checks:
            check_name = check.get('check_name', '')
            module_x_value = check.get('module_x', '')
            module_y_value = check.get('module_y', '')
            # Per-check technician/QC names, falling back to process-level params
            check_technician = check.get('technician_name', '') or technician_name
            check_qc = check.get('qc_name', '') or qc_name
            # Per-check remarks, falling back to process-level remarks param
            check_remarks = check.get('remarks', '') or remarks

            # Check if this check already exists
            if is_postgres:
                cur.execute("""
                    SELECT id, module_x, module_y FROM qc_checks
                    WHERE pack_id = %s AND process_name = %s AND check_name = %s
                    LIMIT 1
                """, (pack_id, process_name, check_name))
            else:
                cur.execute("""
                    SELECT id, module_x, module_y FROM qc_checks
                    WHERE pack_id = ? AND process_name = ? AND check_name = ?
                    LIMIT 1
                """, (pack_id, process_name, check_name))

            existing_row = cur.fetchone()

            if existing_row:
                # Row exists - UPDATE only fields that have data
                row_id = existing_row[0]
                existing_module_x = existing_row[1] if len(existing_row) > 1 else ''
                existing_module_y = existing_row[2] if len(existing_row) > 2 else ''

                # Merge logic: Keep existing data if new data is empty
                final_module_x = module_x_value if module_x_value else existing_module_x
                final_module_y = module_y_value if module_y_value else existing_module_y

                # Auto-complete: set end_date when both modules filled, clear it if either is empty
                check_is_complete = bool(final_module_x) and bool(final_module_y)
                check_end_date = timestamp if check_is_complete else None

                # Update the row with merged data
                if is_postgres:
                    cur.execute("""
                        UPDATE qc_checks
                        SET module_x = %s, module_y = %s,
                            technician_name = %s, qc_name = %s, remarks = %s,
                            end_date = %s, updated_at = %s
                        WHERE id = %s
                    """, (final_module_x, final_module_y, check_technician, check_qc,
                          check_remarks, check_end_date, timestamp, row_id))
                else:
                    cur.execute("""
                        UPDATE qc_checks
                        SET module_x = ?, module_y = ?,
                            technician_name = ?, qc_name = ?, remarks = ?,
                            end_date = ?, updated_at = ?
                        WHERE id = ?
                    """, (final_module_x, final_module_y, check_technician, check_qc,
                          check_remarks, check_end_date, timestamp, row_id))

                logger.debug(f"Updated check '{check_name}' - Module X: '{final_module_x}', Module Y: '{final_module_y}', auto-complete: {check_is_complete}")

            else:
                # Row doesn't exist - INSERT new row
                # Auto-complete: set end_date immediately if both modules are filled on insert
                check_is_complete = bool(module_x_value) and bool(module_y_value)
                check_end_date = timestamp if check_is_complete else None

                if is_postgres:
                    cur.execute("""
                        INSERT INTO qc_checks
                        (pack_id, process_name, check_name, module_x, module_y,
                         technician_name, qc_name, remarks, start_date, end_date, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (pack_id, process_name, check_name,
                          module_x_value, module_y_value,
                          check_technician, check_qc, check_remarks,
                          timestamp, check_end_date, timestamp, timestamp))
                else:
                    cur.execute("""
                        INSERT INTO qc_checks
                        (pack_id, process_name, check_name, module_x, module_y,
                         technician_name, qc_name, remarks, start_date, end_date, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (pack_id, process_name, check_name,
                          module_x_value, module_y_value,
                          check_technician, check_qc, check_remarks,
                          timestamp, check_end_date, timestamp, timestamp))

                logger.debug(f"Inserted new check '{check_name}' - Module X: '{module_x_value}', Module Y: '{module_y_value}', auto-complete: {check_is_complete}")

        conn.commit()
        logger.info(f"Saved/merged {len(checks)} QC checks for {pack_id} - {process_name}")
        return True

    except Exception as e:
        logger.error(f"Error saving QC checks: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)


@retry_on_db_lock
def update_process_completion(pack_id: str, process_name: str) -> bool:
    """Update end_date for a process with retry on lock (handles concurrent updates)"""
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
            # Use immediate transaction for write lock
            conn.isolation_level = 'IMMEDIATE'
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
    """
    Check if process has data and completion status
    Enhanced to check if BOTH modules are complete
    """
    result = {
        'exists': False,
        'started': False,
        'completed': False,
        'process_type': None,
        'both_modules_complete': False,
        'module_x_complete': False,
        'module_y_complete': False,
        'has_any_data': False,
        'completed_checks': 0,
        'total_checks': 0
    }

    try:
        from app_unified_db import PROCESS_ROW_MAPPING, PROCESS_DEFINITIONS
        process_info = PROCESS_ROW_MAPPING.get(process_name)
        if not process_info:
            return result

        result['process_type'] = process_info['type']
        checks = get_qc_checks(pack_id, process_name)

        # Total expected checks comes from PROCESS_DEFINITIONS, not just DB rows.
        # This ensures completion is only True when every defined check has been saved.
        expected_checks = PROCESS_DEFINITIONS.get(process_name, {}).get('qc_checks', [])
        expected_total = len(expected_checks) if expected_checks else len(checks)

        if checks:
            result['exists'] = True
            result['has_any_data'] = True
            result['started'] = any(check.get('start_date') for check in checks)

            # Process is complete only when ALL defined checks have their individual end_date set
            completed_checks = sum(1 for c in checks if c.get('end_date'))
            result['completed'] = (completed_checks == expected_total) and expected_total > 0
            result['completed_checks'] = completed_checks
            result['total_checks'] = expected_total

            # Check if both modules are complete (all non-empty; N/A counts as a valid deliberate entry)
            module_x_count = 0
            module_y_count = 0

            for check in checks:
                module_x = check.get('module_x', '').strip()
                module_y = check.get('module_y', '').strip()

                # Any non-empty value counts (OK, NOT OK, N/A are all deliberate choices)
                if module_x:
                    module_x_count += 1
                if module_y:
                    module_y_count += 1

            # Module is complete if all checks have data
            result['module_x_complete'] = module_x_count == expected_total
            result['module_y_complete'] = module_y_count == expected_total
            result['both_modules_complete'] = result['module_x_complete'] and result['module_y_complete']

            logger.debug(f"Process status for {pack_id}-{process_name}: "
                        f"Module X: {module_x_count}/{expected_total}, "
                        f"Module Y: {module_y_count}/{expected_total}, "
                        f"Completed checks: {completed_checks}/{expected_total}")

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


def get_not_ok_checks(pack_id: str, process_names: list) -> list:
    """
    Query qc_checks for NOT OK results in specified processes for a battery pack.
    Returns list of dicts: {process_name, check_name, module} for each NOT OK finding.
    """
    if not process_names:
        return []

    conn = get_connection()
    db_url = get_database_url()
    is_postgres = db_url.startswith('postgres')

    try:
        cur = conn.cursor()
        results = []

        if is_postgres:
            placeholders = ','.join(['%s'] * len(process_names))
            cur.execute(f"""
                SELECT process_name, check_name, module_x, module_y
                FROM qc_checks
                WHERE pack_id = %s AND process_name IN ({placeholders})
                ORDER BY process_name, created_at ASC
            """, [pack_id] + process_names)
        else:
            placeholders = ','.join(['?'] * len(process_names))
            cur.execute(f"""
                SELECT process_name, check_name, module_x, module_y
                FROM qc_checks
                WHERE pack_id = ? AND process_name IN ({placeholders})
                ORDER BY process_name, created_at ASC
            """, [pack_id] + process_names)

        rows = cur.fetchall()

        for row in rows:
            process_name = row[0]
            check_name = row[1]
            module_x = row[2] or ''
            module_y = row[3] or ''

            if module_x == 'NOT OK':
                results.append({
                    'process_name': process_name,
                    'check_name': check_name,
                    'module': 'Module X'
                })
            if module_y == 'NOT OK':
                results.append({
                    'process_name': process_name,
                    'check_name': check_name,
                    'module': 'Module Y'
                })

        return results

    except Exception as e:
        logger.error(f"Error checking NOT OK status: {e}")
        return []
    finally:
        release_connection(conn)
