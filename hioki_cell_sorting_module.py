"""
HIOKI CELL SORTING - Streamlit Module
Independent tab for Hioki Battery Tester integration
No dependencies on existing MES code or databases
Can be added to any Streamlit app with a single import
"""

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import socket
import logging
from contextlib import contextmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HiokiCellSorting")


class HiokiCellSortingDB:
    """
    Independent database manager for Hioki Cell Sorting.
    Uses its own SQLite database - NO connection to MES database.
    """

    def __init__(self, db_path: str = "hioki_cell_sorting.db") -> None:
        """Initialize with independent database."""
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Create all required tables in independent database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Measurements table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS measurements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT UNIQUE NOT NULL,
                        voltage REAL NOT NULL,
                        resistance REAL NOT NULL,
                        device_name TEXT DEFAULT 'Hioki BT3562A',
                        notes TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Daily statistics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT UNIQUE NOT NULL,
                        total_scans INTEGER DEFAULT 0,
                        avg_voltage REAL,
                        avg_resistance REAL,
                        min_voltage REAL,
                        max_voltage REAL,
                        min_resistance REAL,
                        max_resistance REAL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Report history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS report_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_name TEXT NOT NULL,
                        generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        date_range_start TEXT,
                        date_range_end TEXT,
                        total_records INTEGER,
                        file_path TEXT
                    )
                ''')

                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def add_measurement(
        self,
        timestamp: str,
        voltage: float,
        resistance: float,
        device_name: str = "Hioki BT3562A",
        notes: str = "",
    ) -> bool:
        """
        Add a new measurement to the database.

        Args:
            timestamp: ISO format datetime string (unique per record).
            voltage: Measured voltage in Volts (0–30V).
            resistance: Measured resistance in Ohms (0–10000Ω).
            device_name: Name of the measurement device.
            notes: Optional free-text notes.

        Returns:
            True on success, False on failure.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT OR IGNORE INTO measurements
                    (timestamp, voltage, resistance, device_name, notes)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (timestamp, voltage, resistance, device_name, notes),
                )
                conn.commit()
                logger.info(f"Added measurement: {voltage}V, {resistance}Ω")
                return True
        except Exception as e:
            logger.error(f"Failed to add measurement: {e}")
            return False

    def get_measurements(
        self, days: int | None = None, limit: int | None = None
    ) -> pd.DataFrame:
        """
        Retrieve measurements from the database.

        Args:
            days: If set, only return records from the last N days.
            limit: Maximum number of records to return (newest first).

        Returns:
            DataFrame of measurements.
        """
        try:
            with self.get_connection() as conn:
                query = "SELECT * FROM measurements"
                params: list = []

                if days:
                    query += " WHERE timestamp > datetime('now', ?)"
                    params.append(f"-{days} days")

                query += " ORDER BY timestamp DESC"

                if limit:
                    query += " LIMIT ?"
                    params.append(limit)

                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            logger.error(f"Failed to get measurements: {e}")
            return pd.DataFrame()

    def get_today_stats(self) -> dict | None:
        """
        Return aggregated statistics for today.

        Returns:
            Dict with keys total_scans, avg_voltage, avg_resistance,
            min_voltage, max_voltage, min_resistance, max_resistance,
            or None if no data exists for today.
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT
                        COUNT(*)          AS total_scans,
                        AVG(voltage)      AS avg_voltage,
                        AVG(resistance)   AS avg_resistance,
                        MIN(voltage)      AS min_voltage,
                        MAX(voltage)      AS max_voltage,
                        MIN(resistance)   AS min_resistance,
                        MAX(resistance)   AS max_resistance
                    FROM measurements
                    WHERE DATE(timestamp) = ?
                    ''',
                    (today,),
                )
                row = cursor.fetchone()
                if row and row[0] > 0:
                    return {
                        "total_scans": row[0],
                        "avg_voltage": row[1],
                        "avg_resistance": row[2],
                        "min_voltage": row[3],
                        "max_voltage": row[4],
                        "min_resistance": row[5],
                        "max_resistance": row[6],
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get today's stats: {e}")
            return None

    def get_total_count(self) -> int:
        """Return total number of stored measurements."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM measurements")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to count measurements: {e}")
            return 0

    def export_csv(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame | None:
        """
        Export measurements as a DataFrame (for CSV download).

        Args:
            start_date: Inclusive start date string 'YYYY-MM-DD'.
            end_date: Inclusive end date string 'YYYY-MM-DD'.

        Returns:
            DataFrame of matching records, or None on error.
        """
        try:
            with self.get_connection() as conn:
                query = "SELECT * FROM measurements"
                params: list = []

                if start_date and end_date:
                    query += " WHERE DATE(timestamp) BETWEEN ? AND ?"
                    params = [start_date, end_date]

                query += " ORDER BY timestamp"
                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return None

    def export_excel(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame | None:
        """
        Export measurements as a DataFrame (for Excel download).

        Delegates to export_csv; callers write to an Excel buffer.
        """
        return self.export_csv(start_date, end_date)


class NetworkCheck:
    """Detect whether the machine is on the office LAN."""

    @staticmethod
    def is_office_network(office_subnet: str = "192.168") -> bool:
        """
        Check if the current host IP starts with the given subnet prefix.

        Args:
            office_subnet: IP prefix that identifies the office network.

        Returns:
            True if on the office network, False otherwise.
        """
        try:
            hostname = socket.gethostbyname(socket.gethostname())
            connected = hostname.startswith(office_subnet)
            logger.info(f"Network check — IP: {hostname}, office: {connected}")
            return connected
        except Exception as e:
            logger.warning(f"Network check failed: {e}")
            return False


# ---------------------------------------------------------------------------
# Main Streamlit component
# ---------------------------------------------------------------------------

def render_hioki_cell_sorting_tab(
    db_path: str = "hioki_cell_sorting.db",
    office_subnet: str = "192.168",
) -> None:
    """
    Render the Hioki Cell Sorting tab inside the calling Streamlit app.

    Usage in your main app
    ----------------------
    from hioki_cell_sorting_module import render_hioki_cell_sorting_tab

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Data Entry", "QR Generator", "Dashboard", "Reports", "Cell Sorting"]
    )
    with tab5:
        render_hioki_cell_sorting_tab()

    Args:
        db_path: Path to the independent SQLite database file.
        office_subnet: IP prefix used to detect the office network.
    """

    # ---------- initialise ----------
    db = HiokiCellSortingDB(db_path)
    is_office = NetworkCheck.is_office_network(office_subnet)

    # ---------- header ----------
    col_title, col_network, col_refresh = st.columns([3, 1, 1])
    with col_title:
        st.markdown("## 🔋 Cell Sorting — Hioki Battery Tester")
    with col_network:
        if is_office:
            st.success("🟢 Office Network", help="Data can be synced")
        else:
            st.error("🔴 Not on Office Network", help="Limited functionality")
    with col_refresh:
        if st.button("🔄 Refresh", help="Refresh data", key="hioki_refresh"):
            st.rerun()

    # ---------- sub-tabs ----------
    dash_tab, add_tab, hist_tab, rep_tab = st.tabs([
        "📊 Dashboard",
        "📝 Add Measurement",
        "📈 History",
        "📄 Reports",
    ])

    # ======================================================
    # TAB 1 — DASHBOARD
    # ======================================================
    with dash_tab:
        st.subheader("Real-time Dashboard")

        stats = db.get_today_stats()
        total = db.get_total_count()

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Stored", total)
        with col2:
            st.metric("Today's Scans", stats["total_scans"] if stats else 0)
        with col3:
            st.metric(
                "Avg Voltage",
                f"{stats['avg_voltage']:.2f} V" if stats else "— V",
            )
        with col4:
            st.metric(
                "Avg Resistance",
                f"{stats['avg_resistance']:.2f} Ω" if stats else "— Ω",
            )
        with col5:
            if stats:
                v_range = stats["max_voltage"] - stats["min_voltage"]
                st.metric("Voltage Range", f"{v_range:.2f} V")
            else:
                st.metric("Voltage Range", "— V")

        st.subheader("Latest 10 Measurements")
        df_latest = db.get_measurements(limit=10)

        if not df_latest.empty:
            df_display = df_latest[
                ["timestamp", "voltage", "resistance", "device_name", "notes"]
            ].copy()
            df_display.columns = ["Time", "Voltage (V)", "Resistance (Ω)", "Device", "Notes"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("📭 No measurements recorded yet. Use the **Add Measurement** tab.")

        if len(df_latest) > 2:
            st.subheader("Trends")
            df_latest["timestamp"] = pd.to_datetime(df_latest["timestamp"])
            df_sorted = df_latest.sort_values("timestamp")

            col_v, col_r = st.columns(2)
            with col_v:
                st.line_chart(
                    df_sorted.set_index("timestamp")[["voltage"]],
                    use_container_width=True,
                )
                st.caption("Voltage trend (V)")
            with col_r:
                st.line_chart(
                    df_sorted.set_index("timestamp")[["resistance"]],
                    use_container_width=True,
                )
                st.caption("Resistance trend (Ω)")

    # ======================================================
    # TAB 2 — ADD MEASUREMENT
    # ======================================================
    with add_tab:
        st.subheader("📝 Add New Measurement")

        if not is_office:
            st.warning(
                "⚠️ Not on office network — data will be stored locally "
                "and can be synced once you reconnect."
            )

        col_v, col_r = st.columns(2)
        with col_v:
            voltage = st.number_input(
                "Voltage (V)",
                min_value=0.0,
                max_value=30.0,
                step=0.01,
                format="%.2f",
                key="hioki_voltage",
            )
        with col_r:
            resistance = st.number_input(
                "Resistance (Ω)",
                min_value=0.0,
                max_value=10000.0,
                step=0.1,
                format="%.2f",
                key="hioki_resistance",
            )

        device_name = st.text_input(
            "Device Name",
            value="Hioki BT3562A",
            help="Device that produced this measurement",
            key="hioki_device",
        )

        notes = st.text_area(
            "Notes (optional)",
            placeholder="Add any notes about this measurement…",
            height=100,
            key="hioki_notes",
        )

        col_btn, col_info = st.columns([1, 4])
        with col_btn:
            if st.button("💾 Save", use_container_width=True, key="hioki_save"):
                timestamp = datetime.now().isoformat()
                if db.add_measurement(timestamp, voltage, resistance, device_name, notes):
                    st.success("✅ Measurement saved!")
                    st.balloons()
                else:
                    st.error("❌ Failed to save measurement — check the logs.")
        with col_info:
            st.info(
                "📌 Stored in an independent database (`hioki_cell_sorting.db`). "
                "No existing MES data is affected.",
                icon="ℹ️",
            )

    # ======================================================
    # TAB 3 — HISTORY
    # ======================================================
    with hist_tab:
        st.subheader("📈 Measurement History")

        col_days, col_sort, col_lim = st.columns(3)
        with col_days:
            days = st.selectbox(
                "Filter by days",
                [1, 7, 30, 90, 365],
                index=1,
                key="hioki_days",
            )
        with col_sort:
            sort_order = st.radio(
                "Sort order",
                ["Newest First", "Oldest First"],
                horizontal=True,
                key="hioki_sort",
            )
        with col_lim:
            limit = st.number_input(
                "Max records",
                min_value=10,
                max_value=1000,
                value=100,
                key="hioki_limit",
            )

        df = db.get_measurements(days=days, limit=int(limit))

        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            ascending = sort_order == "Oldest First"
            df = df.sort_values("timestamp", ascending=ascending)

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Records", len(df))
            m2.metric("Avg Voltage", f"{df['voltage'].mean():.2f} V")
            m3.metric("Avg Resistance", f"{df['resistance'].mean():.2f} Ω")

            st.subheader("All Records")
            df_display = df[
                ["timestamp", "voltage", "resistance", "device_name", "notes"]
            ].copy()
            df_display.columns = ["Time", "Voltage (V)", "Resistance (Ω)", "Device", "Notes"]
            df_display["Voltage (V)"] = df_display["Voltage (V)"].map("{:.2f}".format)
            df_display["Resistance (Ω)"] = df_display["Resistance (Ω)"].map("{:.2f}".format)
            st.dataframe(df_display, use_container_width=True, height=400, hide_index=True)
        else:
            st.info("📭 No measurements found for the selected period.")

    # ======================================================
    # TAB 4 — REPORTS
    # ======================================================
    with rep_tab:
        st.subheader("📄 Generate Reports & Export Data")

        col_s, col_e = st.columns(2)
        with col_s:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=7),
                key="hioki_start",
            )
        with col_e:
            end_date = st.date_input(
                "End Date",
                value=datetime.now(),
                key="hioki_end",
            )

        st.markdown("---")
        st.subheader("Export")
        col_csv, col_xlsx, col_sum = st.columns(3)

        with col_csv:
            if st.button("📥 Prepare CSV", use_container_width=True, key="hioki_csv_btn"):
                df_exp = db.export_csv(
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                )
                if df_exp is not None and not df_exp.empty:
                    csv_bytes = df_exp.to_csv(index=False).encode()
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv_bytes,
                        file_name=f"hioki_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="hioki_csv_dl",
                    )
                else:
                    st.warning("No data in the selected date range.")

        with col_xlsx:
            if st.button("📥 Prepare Excel", use_container_width=True, key="hioki_xlsx_btn"):
                df_exp = db.export_excel(
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                )
                if df_exp is not None and not df_exp.empty:
                    import io
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        df_exp.to_excel(writer, index=False, sheet_name="Measurements")
                    st.download_button(
                        label="⬇️ Download Excel",
                        data=buf.getvalue(),
                        file_name=f"hioki_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="hioki_xlsx_dl",
                    )
                else:
                    st.warning("No data in the selected date range.")

        with col_sum:
            if st.button("📋 Summary Report", use_container_width=True, key="hioki_sum_btn"):
                df_exp = db.export_csv(
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                )
                if df_exp is not None and not df_exp.empty:
                    st.markdown("---")
                    st.markdown("### 📊 Summary Report")
                    st.markdown(f"**Date Range:** {start_date} → {end_date}")
                    st.markdown(f"**Total Measurements:** {len(df_exp)}")
                    st.markdown(
                        f"**Voltage:** avg {df_exp['voltage'].mean():.2f} V &nbsp;|&nbsp; "
                        f"range {df_exp['voltage'].min():.2f}–{df_exp['voltage'].max():.2f} V"
                    )
                    st.markdown(
                        f"**Resistance:** avg {df_exp['resistance'].mean():.2f} Ω &nbsp;|&nbsp; "
                        f"range {df_exp['resistance'].min():.2f}–{df_exp['resistance'].max():.2f} Ω"
                    )
                else:
                    st.warning("No data available for the selected date range.")

    # ---------- footer ----------
    st.divider()
    col_info, col_clear = st.columns(2)
    with col_info:
        st.caption(f"Database: `{db.db_path}`")
        st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with col_clear:
        if st.button("🗑️ Clear All Data", key="hioki_clear"):
            if st.session_state.get("hioki_confirm_clear"):
                try:
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM measurements")
                        cursor.execute("DELETE FROM daily_stats")
                        conn.commit()
                    st.session_state["hioki_confirm_clear"] = False
                    st.success("✅ All data cleared.")
                except Exception as e:
                    st.error(f"❌ Error clearing data: {e}")
            else:
                st.session_state["hioki_confirm_clear"] = True
                st.warning("⚠️ Click **Clear All Data** again to confirm permanent deletion.")


# ---------------------------------------------------------------------------
# Standalone entry-point for quick testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    st.set_page_config(page_title="Hioki Cell Sorting", layout="wide")
    render_hioki_cell_sorting_tab()
