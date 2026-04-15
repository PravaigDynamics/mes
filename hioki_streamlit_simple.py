"""
HIOKI CELL SORTING — Streamlit UI
==================================
Reads from the independent SQLite database written by hioki_simple_receiver.py.

The receiver is a SEPARATE process on the server — this module only reads from
the shared database; it never starts or stops the receiver itself.

Usage in your main Streamlit app:
    from hioki_streamlit_simple import render_hioki_cell_sorting_tab

    with tab_cell_sorting:
        render_hioki_cell_sorting_tab()

Optional arguments:
    render_hioki_cell_sorting_tab(
        db_path="hioki_measurements.db",   # path to the receiver's DB
        office_subnet="192.168",           # prefix to detect office LAN
        receiver_port=5000,                # port the receiver listens on
    )
"""

import io
import socket
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

logger = logging.getLogger("HiokiCellSorting")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DB = "hioki_measurements.db"
DEFAULT_SUBNET = "192.168"
DEFAULT_PORT = 5000


# ---------------------------------------------------------------------------
# DB helpers (read-only views — writing is done by the receiver process)
# ---------------------------------------------------------------------------

class _DB:
    """Thin read-only wrapper around the receiver's SQLite database."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Create tables only if the DB file is brand-new (first run)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
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
        except Exception as exc:
            logger.error(f"DB init error: {exc}")

    def get_measurements(
        self,
        days: int | None = None,
        limit: int | None = None,
        ascending: bool = False,
    ) -> pd.DataFrame:
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM measurements"
                params: list = []
                if days:
                    query += " WHERE timestamp > datetime('now', ?)"
                    params.append(f"-{days} days")
                order = "ASC" if ascending else "DESC"
                query += f" ORDER BY timestamp {order}"
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                return pd.read_sql_query(query, conn, params=params)
        except Exception as exc:
            logger.error(f"Query error: {exc}")
            return pd.DataFrame()

    def get_today_stats(self) -> dict | None:
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    '''
                    SELECT COUNT(*), AVG(voltage), AVG(resistance),
                           MIN(voltage), MAX(voltage),
                           MIN(resistance), MAX(resistance)
                    FROM measurements
                    WHERE DATE(timestamp) = ?
                    ''',
                    (today,),
                ).fetchone()
            if row and row[0]:
                return dict(
                    zip(
                        ["total", "avg_v", "avg_r", "min_v", "max_v", "min_r", "max_r"],
                        row,
                    )
                )
        except Exception as exc:
            logger.error(f"Stats error: {exc}")
        return None

    def get_total_count(self) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                return conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
        except Exception:
            return 0

    def add_manual(
        self,
        voltage: float,
        resistance: float,
        device_name: str,
        notes: str,
    ) -> bool:
        """Insert a manually entered measurement (for testing / offline use)."""
        ts = datetime.now().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    '''
                    INSERT OR IGNORE INTO measurements
                        (timestamp, voltage, resistance, device_name, notes)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (ts, voltage, resistance, device_name, notes),
                )
                conn.commit()
            return True
        except Exception as exc:
            logger.error(f"Manual insert error: {exc}")
            return False

    def export_range(self, start: str, end: str) -> pd.DataFrame:
        try:
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(
                    "SELECT * FROM measurements WHERE DATE(timestamp) BETWEEN ? AND ? ORDER BY timestamp",
                    conn,
                    params=[start, end],
                )
        except Exception as exc:
            logger.error(f"Export error: {exc}")
            return pd.DataFrame()

    def clear_all(self) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM measurements")
                conn.execute("DELETE FROM daily_stats")
                conn.commit()
            return True
        except Exception as exc:
            logger.error(f"Clear error: {exc}")
            return False


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def _on_office_network(subnet: str) -> bool:
    """Return True if this machine's IP starts with *subnet*."""
    try:
        ip = socket.gethostbyname(socket.gethostname())
        return ip.startswith(subnet)
    except Exception:
        return False


def _receiver_running(port: int) -> bool:
    """
    Return True if something is already listening on *port* locally.
    A successful connect means the receiver process is up.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            return False


# ---------------------------------------------------------------------------
# Main Streamlit component
# ---------------------------------------------------------------------------

def render_hioki_cell_sorting_tab(
    db_path: str = DEFAULT_DB,
    office_subnet: str = DEFAULT_SUBNET,
    receiver_port: int = DEFAULT_PORT,
) -> None:
    """
    Render the full Cell Sorting tab.

    The receiver is a separate process — this function only reads the shared DB.
    """
    db = _DB(db_path)
    on_office = _on_office_network(office_subnet)
    recv_up = _receiver_running(receiver_port)

    # ── Header ──────────────────────────────────────────────────────────────
    h1, h2, h3, h4 = st.columns([3, 1, 1, 1])
    with h1:
        st.markdown("## 🔋 Cell Sorting — Hioki Battery Tester")
    with h2:
        if on_office:
            st.success("🟢 Office LAN")
        else:
            st.error("🔴 Off-network")
    with h3:
        if recv_up:
            st.success(f"🟢 Receiver :{receiver_port}")
        else:
            st.warning(f"🟡 Receiver :{receiver_port} down")
    with h4:
        if st.button("🔄 Refresh", key="hioki_refresh"):
            st.rerun()

    if not recv_up:
        st.info(
            f"**Receiver not detected on port {receiver_port}.**  "
            "Start it on the server with:  \n"
            f"`python hioki_simple_receiver.py --port {receiver_port}`",
            icon="ℹ️",
        )

    # ── Sub-tabs ─────────────────────────────────────────────────────────────
    dash_tab, manual_tab, hist_tab, rep_tab = st.tabs([
        "📊 Dashboard",
        "📝 Add / Test",
        "📈 History",
        "📄 Reports",
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — DASHBOARD
    # ════════════════════════════════════════════════════════════════════════
    with dash_tab:
        st.subheader("Real-time Dashboard")

        stats = db.get_today_stats()
        total = db.get_total_count()

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Stored", total)
        c2.metric("Today's Scans", stats["total"] if stats else 0)
        c3.metric("Avg Voltage", f"{stats['avg_v']:.2f} V" if stats else "— V")
        c4.metric("Avg Resistance", f"{stats['avg_r']:.2f} Ω" if stats else "— Ω")
        if stats:
            c5.metric("Voltage Range", f"{stats['max_v'] - stats['min_v']:.2f} V")
        else:
            c5.metric("Voltage Range", "— V")

        st.subheader("Latest 10 Measurements")
        df_latest = db.get_measurements(limit=10)

        if not df_latest.empty:
            disp = df_latest[["timestamp", "voltage", "resistance", "device_name", "notes"]].copy()
            disp.columns = ["Time", "Voltage (V)", "Resistance (Ω)", "Device", "Notes"]
            st.dataframe(disp, use_container_width=True, hide_index=True)

            if len(df_latest) > 2:
                st.subheader("Trends")
                df_sorted = df_latest.copy()
                df_sorted["timestamp"] = pd.to_datetime(df_sorted["timestamp"])
                df_sorted = df_sorted.sort_values("timestamp")
                col_v, col_r = st.columns(2)
                with col_v:
                    st.line_chart(df_sorted.set_index("timestamp")[["voltage"]], use_container_width=True)
                    st.caption("Voltage trend (V)")
                with col_r:
                    st.line_chart(df_sorted.set_index("timestamp")[["resistance"]], use_container_width=True)
                    st.caption("Resistance trend (Ω)")
        else:
            st.info(
                "📭 No measurements yet.  \n"
                "Waiting for data from the Hioki device via the receiver,  \n"
                "or add a test entry in the **Add / Test** tab."
            )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — MANUAL / TEST ENTRY
    # (useful when Hioki is not connected or for verifying the pipeline)
    # ════════════════════════════════════════════════════════════════════════
    with manual_tab:
        st.subheader("📝 Manual / Test Measurement Entry")
        st.caption(
            "Use this tab to add measurements manually (for testing when "
            "the Hioki device is not connected, or for offline data entry)."
        )

        if not on_office:
            st.warning("⚠️ Not on office network — data stored locally only.")

        col_v, col_r = st.columns(2)
        with col_v:
            voltage = st.number_input("Voltage (V)", min_value=0.0, max_value=30.0,
                                      step=0.01, format="%.4f", key="hioki_manual_v")
        with col_r:
            resistance = st.number_input("Resistance (Ω)", min_value=0.0, max_value=10000.0,
                                         step=0.1, format="%.2f", key="hioki_manual_r")

        device_name = st.text_input("Device Name", value="Hioki BT3562A", key="hioki_dev")
        notes = st.text_area("Notes (optional)", height=80, key="hioki_notes",
                             placeholder="e.g. Cell ID, batch number…")

        col_btn, col_info = st.columns([1, 4])
        with col_btn:
            if st.button("💾 Save", use_container_width=True, key="hioki_save"):
                if db.add_manual(voltage, resistance, device_name, notes):
                    st.success("✅ Saved!")
                    st.balloons()
                else:
                    st.error("❌ Save failed — check logs.")
        with col_info:
            st.info(
                "📌 Stored in `hioki_measurements.db` — fully isolated from the MES database.",
                icon="ℹ️",
            )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — HISTORY
    # ════════════════════════════════════════════════════════════════════════
    with hist_tab:
        st.subheader("📈 Measurement History")

        col_d, col_s, col_l = st.columns(3)
        with col_d:
            days = st.selectbox("Period", [1, 7, 30, 90, 365], index=1, key="hioki_days")
        with col_s:
            asc = st.radio("Sort", ["Newest First", "Oldest First"],
                           horizontal=True, key="hioki_sort") == "Oldest First"
        with col_l:
            limit = int(st.number_input("Max rows", 10, 1000, 200, key="hioki_lim"))

        df = db.get_measurements(days=days, limit=limit, ascending=asc)

        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            m1, m2, m3 = st.columns(3)
            m1.metric("Records", len(df))
            m2.metric("Avg Voltage", f"{df['voltage'].mean():.2f} V")
            m3.metric("Avg Resistance", f"{df['resistance'].mean():.2f} Ω")

            disp = df[["timestamp", "voltage", "resistance", "device_name", "notes"]].copy()
            disp.columns = ["Time", "Voltage (V)", "Resistance (Ω)", "Device", "Notes"]
            disp["Voltage (V)"] = disp["Voltage (V)"].map("{:.4f}".format)
            disp["Resistance (Ω)"] = disp["Resistance (Ω)"].map("{:.2f}".format)
            st.dataframe(disp, use_container_width=True, height=420, hide_index=True)
        else:
            st.info("📭 No records found for the selected period.")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4 — REPORTS & EXPORT
    # ════════════════════════════════════════════════════════════════════════
    with rep_tab:
        st.subheader("📄 Export & Reports")

        col_s, col_e = st.columns(2)
        with col_s:
            start_date = st.date_input("Start Date",
                                       value=datetime.now() - timedelta(days=7),
                                       key="hioki_start")
        with col_e:
            end_date = st.date_input("End Date", value=datetime.now(), key="hioki_end")

        st.markdown("---")

        col_csv, col_xlsx, col_sum = st.columns(3)

        with col_csv:
            if st.button("📥 Prepare CSV", use_container_width=True, key="hioki_csv_btn"):
                df_exp = db.export_range(start_date.strftime("%Y-%m-%d"),
                                         end_date.strftime("%Y-%m-%d"))
                if not df_exp.empty:
                    st.download_button(
                        "⬇️ Download CSV",
                        data=df_exp.to_csv(index=False).encode(),
                        file_name=f"hioki_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="hioki_csv_dl",
                    )
                else:
                    st.warning("No data in this date range.")

        with col_xlsx:
            if st.button("📥 Prepare Excel", use_container_width=True, key="hioki_xlsx_btn"):
                df_exp = db.export_range(start_date.strftime("%Y-%m-%d"),
                                          end_date.strftime("%Y-%m-%d"))
                if not df_exp.empty:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        df_exp.to_excel(writer, index=False, sheet_name="Measurements")
                    st.download_button(
                        "⬇️ Download Excel",
                        data=buf.getvalue(),
                        file_name=f"hioki_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="hioki_xlsx_dl",
                    )
                else:
                    st.warning("No data in this date range.")

        with col_sum:
            if st.button("📋 Summary", use_container_width=True, key="hioki_sum_btn"):
                df_exp = db.export_range(start_date.strftime("%Y-%m-%d"),
                                          end_date.strftime("%Y-%m-%d"))
                if not df_exp.empty:
                    st.markdown("---")
                    st.markdown("### 📊 Summary Report")
                    st.markdown(f"**Period:** {start_date} → {end_date}")
                    st.markdown(f"**Total measurements:** {len(df_exp)}")
                    st.markdown(
                        f"**Voltage:** avg {df_exp['voltage'].mean():.4f} V &nbsp;|&nbsp; "
                        f"range {df_exp['voltage'].min():.4f} – {df_exp['voltage'].max():.4f} V"
                    )
                    st.markdown(
                        f"**Resistance:** avg {df_exp['resistance'].mean():.2f} Ω &nbsp;|&nbsp; "
                        f"range {df_exp['resistance'].min():.2f} – {df_exp['resistance'].max():.2f} Ω"
                    )
                else:
                    st.warning("No data in this date range.")

    # ── Footer ───────────────────────────────────────────────────────────────
    st.divider()
    col_inf, col_clr = st.columns(2)
    with col_inf:
        st.caption(f"Database: `{Path(db_path).resolve()}`")
        st.caption(f"Receiver port: {receiver_port}  |  "
                   f"Status: {'running' if recv_up else 'stopped'}")
        st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with col_clr:
        if st.button("🗑️ Clear All Data", key="hioki_clear"):
            if st.session_state.get("hioki_confirm_clear"):
                if db.clear_all():
                    st.success("✅ All data cleared.")
                else:
                    st.error("❌ Failed to clear data.")
                st.session_state["hioki_confirm_clear"] = False
            else:
                st.session_state["hioki_confirm_clear"] = True
                st.warning("⚠️ Click **Clear All Data** again to confirm.")


# ---------------------------------------------------------------------------
# Standalone entry-point for quick testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    st.set_page_config(page_title="Hioki Cell Sorting", layout="wide")
    render_hioki_cell_sorting_tab()
