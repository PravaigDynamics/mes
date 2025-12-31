"""
Database Backup Manager for Battery Pack MES
Handles automatic and manual backups of the SQLite database
"""

import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


def create_backup(backup_dir: str = "backups", keep_count: int = 30) -> Optional[Path]:
    """
    Create a timestamped backup of the database

    Args:
        backup_dir: Directory to store backups
        keep_count: Number of backups to retain (deletes oldest)

    Returns:
        Path to created backup file, or None if failed
    """
    try:
        db_path = Path("battery_mes.db")
        if not db_path.exists():
            logger.warning("Database file not found - nothing to backup")
            return None

        # Create backup directory
        backup_path = Path(backup_dir)
        backup_path.mkdir(exist_ok=True)

        # Create timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"battery_mes_backup_{timestamp}.db"

        # Copy database file (copy without preserving metadata to get current timestamp)
        shutil.copy(db_path, backup_file)

        logger.info(f"Database backup created: {backup_file}")

        # Cleanup old backups
        cleanup_old_backups(backup_path, keep_count)

        return backup_file

    except Exception as e:
        logger.error(f"Backup failed: {e}", exc_info=True)
        return None


def cleanup_old_backups(backup_dir: Path, keep_count: int = 30) -> int:
    """
    Remove old backup files, keeping only the most recent ones

    Args:
        backup_dir: Directory containing backups
        keep_count: Number of backups to keep

    Returns:
        Number of files deleted
    """
    try:
        # Get all backup files sorted by modification time (newest first)
        backups = sorted(
            backup_dir.glob("battery_mes_backup_*.db"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        # Delete old backups
        deleted_count = 0
        for old_backup in backups[keep_count:]:
            old_backup.unlink()
            deleted_count += 1
            logger.debug(f"Deleted old backup: {old_backup.name}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old backup(s)")

        return deleted_count

    except Exception as e:
        logger.error(f"Error cleaning up backups: {e}")
        return 0


def list_backups(backup_dir: str = "backups") -> List[dict]:
    """
    List all available backups with details

    Args:
        backup_dir: Directory containing backups

    Returns:
        List of backup info dictionaries
    """
    try:
        backup_path = Path(backup_dir)
        if not backup_path.exists():
            return []

        backups = []
        for backup_file in sorted(backup_path.glob("battery_mes_backup_*.db"), reverse=True):
            stat = backup_file.stat()
            backups.append({
                'filename': backup_file.name,
                'path': str(backup_file),
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created': datetime.fromtimestamp(stat.st_mtime),
                'age_days': (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
            })

        return backups

    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        return []


def restore_backup(backup_file: Path, target_db: str = "battery_mes.db") -> bool:
    """
    Restore database from a backup file

    Args:
        backup_file: Path to backup file to restore
        target_db: Target database filename

    Returns:
        True if successful, False otherwise
    """
    try:
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_file}")
            return False

        target_path = Path(target_db)

        # Create backup of current database before overwriting
        if target_path.exists():
            current_backup = Path(f"{target_db}.before_restore")
            shutil.copy(target_path, current_backup)
            logger.info(f"Current database backed up to: {current_backup}")

        # Restore from backup
        shutil.copy(backup_file, target_path)

        logger.info(f"Database restored from: {backup_file}")
        return True

    except Exception as e:
        logger.error(f"Restore failed: {e}", exc_info=True)
        return False


def get_database_size() -> float:
    """
    Get current database file size in MB

    Returns:
        Size in megabytes
    """
    try:
        db_path = Path("battery_mes.db")
        if not db_path.exists():
            return 0.0

        return round(db_path.stat().st_size / (1024 * 1024), 2)

    except Exception as e:
        logger.error(f"Error getting database size: {e}")
        return 0.0


def verify_backup(backup_file: Path) -> bool:
    """
    Verify that a backup file is a valid SQLite database

    Args:
        backup_file: Path to backup file

    Returns:
        True if valid, False otherwise
    """
    try:
        import sqlite3

        if not backup_file.exists():
            return False

        # Try to open and query the backup
        conn = sqlite3.connect(str(backup_file))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()

        # Should have at least battery_packs and qc_checks tables
        table_names = [t[0] for t in tables]
        has_required_tables = 'battery_packs' in table_names and 'qc_checks' in table_names

        return has_required_tables

    except Exception as e:
        logger.error(f"Backup verification failed: {e}")
        return False


if __name__ == "__main__":
    # Test backup functionality
    logging.basicConfig(level=logging.INFO)

    print("Creating backup...")
    backup_file = create_backup()

    if backup_file:
        print(f"\nBackup created: {backup_file}")
        print(f"Size: {backup_file.stat().st_size / 1024:.2f} KB")

        print("\nVerifying backup...")
        is_valid = verify_backup(backup_file)
        print(f"Backup valid: {is_valid}")

    print("\nListing all backups:")
    backups = list_backups()
    for backup in backups:
        print(f"  - {backup['filename']}: {backup['size_mb']} MB, {backup['age_days']} days old")

    print(f"\nCurrent database size: {get_database_size()} MB")
