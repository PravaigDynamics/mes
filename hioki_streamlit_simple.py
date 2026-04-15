"""
HIOKI CELL SORTING - Streamlit UI
==================================
Reads from the independent SQLite database written by hioki_simple_receiver.py.

The receiver is a SEPARATE process on the server - this module only reads from
the shared database; it never starts or stops the receiver itself.

Usage in your main Streamlit app:
    from hioki_streamlit_simple import render_hioki_cell_sorting_tab

    with tab_cell_sorting:
        render_hioki_cell_sorting_tab()

Compatible with Streamlit >= 1.52 (uses width='stretch' not use_container_width).
"""

import io
import socket
import logging
import sqlite3
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

logger = logging.getLogger("HiokiCellSorting")

DEFAULT_DB = "hioki_measurements.db"
DEFAULT_SUBNET = "192.168"
DEFAULT_PORT = 5000


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

class _DB:
    """Read/write wrapper around the receiver's SQLite database."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self) -> None:
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

    def get_measurements(self, days=None, limit=None, ascending=False):
        with sqlite3.connect(self.db_path) as conn:
            q = "SELECT * FROM measurements"
            p = []
            if days:
                q += " WHERE timestamp > datetime('now', ?)"
                p.append(f"-{days} days")
            q += " ORDER BY timestamp " + ("ASC" if ascending else "DESC")
            if limit:
                q += " LIMIT ?"
                p.append(limit)
            return pd.read_sql_query(q, conn, params=p)

    def get_today_stats(self):
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*), AVG(voltage), AVG(resistance),"
                " MIN(voltage), MAX(voltage), MIN(resistance), MAX(resistance)"
                " FROM measurements WHERE DATE(timestamp) = ?", (today,)
            ).fetchone()
        if row and row[0]:
            keys = ["total", "avg_v", "avg_r", "min_v", "max_v", "min_r", "max_r"]
            return dict(zip(keys, row))
        return None

    def get_total_count(self):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]

    def add_manual(self, voltage, resistance, device_name, notes):
        ts = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO measurements"
                " (timestamp, voltage, resistance, device_name, notes)"
                " VALUES (?, ?, ?, ?, ?)",
                (ts, voltage, resistance, device_name, notes),
            )
            conn.commit()
        return True

    def export_range(self, start, end):
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(
                "SELECT * FROM measurements"
                " WHERE DATE(timestamp) BETWEEN ? AND ?"
                " ORDER BY timestamp",
                conn, params=[start, end],
            )

    def clear_all(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM measurements")
            conn.execute("DELETE FROM daily_stats")
            conn.commit()


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def _on_office_network(subnet):
    try:
        ip = socket.gethostbyname(socket.gethostname())
        return ip.startswith(subnet)
    except Exception:
        return False


def _receiver_running(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Sub-section renderers (called based on radio selection)
# ---------------------------------------------------------------------------

def _render_dashboard(db):
    st.subheader("Real-time Dashboard")
    stats = db.get_today_stats()
    total = db.get_total_count()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Stored", total)
    c2.metric("Today's Scans", stats["total"] if stats else 0)
    c3.metric("Avg Voltage", f"{stats['avg_v']:.4f} V" if stats else "-- V")
    c4.metric("Avg Resistance", f"{stats['avg_r']:.2f} O" if stats else "-- O")
    if stats:
        c5.metric("Voltage Range", f"{stats['max_v'] - stats['min_v']:.4f} V")
    else:
        c5.metric("Voltage Range", "-- V")

    st.subheader("Latest 10 Measurements")
    df = db.get_measurements(limit=10)
    if not df.empty:
        disp = df[["timestamp", "voltage", "resistance", "device_name", "notes"]].copy()
        disp.columns = ["Time", "Voltage (V)", "Resistance (O)", "Device", "Notes"]
        st.dataframe(disp, hide_index=True, width="stretch")

        if len(df) > 2:
            st.subheader("Trends")
            df2 = df.copy()
            df2["timestamp"] = pd.to_datetime(df2["timestamp"])
            df2 = df2.sort_values("timestamp").set_index("timestamp")
            col_v, col_r = st.columns(2)
            with col_v:
                st.line_chart(df2[["voltage"]])
                st.caption("Voltage trend (V)")
            with col_r:
                st.line_chart(df2[["resistance"]])
                st.caption("Resistance trend (O)")
    else:
        st.info(
            "No measurements yet. "
            "Waiting for data from the Hioki device via the receiver, "
            "or add a test entry using 'Add / Test' in the menu above."
        )


def _render_add(db, on_office):
    st.subheader("Add / Test Measurement")
    st.caption(
        "Use this for manual or test entries when the Hioki device is not connected."
    )
    if not on_office:
        st.warning("Not on office network - data stored locally only.")

    col_v, col_r = st.columns(2)
    with col_v:
        voltage = st.number_input(
            "Voltage (V)", min_value=0.0, max_value=30.0,
            step=0.01, format="%.4f", key="hioki_v"
        )
    with col_r:
        resistance = st.number_input(
            "Resistance (O)", min_value=0.0, max_value=10000.0,
            step=0.1, format="%.2f", key="hioki_r"
        )
    device = st.text_input("Device Name", value="Hioki BT3562A", key="hioki_dev")
    notes = st.text_area(
        "Notes (optional)", height=80, key="hioki_notes",
        placeholder="e.g. Cell ID, batch number..."
    )

    if st.button("Save Measurement", key="hioki_save"):
        try:
            db.add_manual(voltage, resistance, device, notes)
            st.success("Saved!")
            st.balloons()
        except Exception as e:
            st.error(f"Save failed: {e}")


def _render_history(db):
    st.subheader("Measurement History")
    col_d, col_s, col_l = st.columns(3)
    with col_d:
        days = st.selectbox("Period", [1, 7, 30, 90, 365], index=1, key="hioki_days")
    with col_s:
        asc = st.radio(
            "Sort", ["Newest First", "Oldest First"],
            horizontal=True, key="hioki_sort"
        ) == "Oldest First"
    with col_l:
        limit = int(st.number_input("Max rows", 10, 1000, 200, key="hioki_lim"))

    df = db.get_measurements(days=days, limit=limit, ascending=asc)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        m1, m2, m3 = st.columns(3)
        m1.metric("Records", len(df))
        m2.metric("Avg Voltage", f"{df['voltage'].mean():.4f} V")
        m3.metric("Avg Resistance", f"{df['resistance'].mean():.2f} O")

        disp = df[["timestamp", "voltage", "resistance", "device_name", "notes"]].copy()
        disp.columns = ["Time", "Voltage (V)", "Resistance (O)", "Device", "Notes"]
        disp["Voltage (V)"] = disp["Voltage (V)"].map("{:.4f}".format)
        disp["Resistance (O)"] = disp["Resistance (O)"].map("{:.2f}".format)
        st.dataframe(disp, height=420, hide_index=True, width="stretch")
    else:
        st.info("No records found for the selected period.")


def _render_reports(db):
    st.subheader("Export and Reports")
    col_s, col_e = st.columns(2)
    with col_s:
        start_date = st.date_input(
            "Start Date", value=datetime.now() - timedelta(days=7), key="hioki_start"
        )
    with col_e:
        end_date = st.date_input("End Date", value=datetime.now(), key="hioki_end")

    st.markdown("---")
    col_csv, col_xlsx, col_sum = st.columns(3)

    with col_csv:
        if st.button("Prepare CSV", key="hioki_csv_btn"):
            df = db.export_range(
                start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )
            if not df.empty:
                st.download_button(
                    "Download CSV",
                    data=df.to_csv(index=False).encode(),
                    file_name=f"hioki_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="hioki_csv_dl",
                )
            else:
                st.warning("No data in this date range.")

    with col_xlsx:
        if st.button("Prepare Excel", key="hioki_xlsx_btn"):
            df = db.export_range(
                start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )
            if not df.empty:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="Measurements")
                st.download_button(
                    "Download Excel",
                    data=buf.getvalue(),
                    file_name=f"hioki_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="hioki_xlsx_dl",
                )
            else:
                st.warning("No data in this date range.")

    with col_sum:
        if st.button("Summary Report", key="hioki_sum_btn"):
            df = db.export_range(
                start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )
            if not df.empty:
                st.markdown("---")
                st.markdown("### Summary Report")
                st.markdown(f"**Period:** {start_date} to {end_date}")
                st.markdown(f"**Total measurements:** {len(df)}")
                st.markdown(
                    f"**Voltage:** avg {df['voltage'].mean():.4f} V | "
                    f"range {df['voltage'].min():.4f} - {df['voltage'].max():.4f} V"
                )
                st.markdown(
                    f"**Resistance:** avg {df['resistance'].mean():.2f} O | "
                    f"range {df['resistance'].min():.2f} - {df['resistance'].max():.2f} O"
                )
            else:
                st.warning("No data in this date range.")


# ---------------------------------------------------------------------------
# Main Streamlit component
# ---------------------------------------------------------------------------

def render_hioki_cell_sorting_tab(
    db_path=DEFAULT_DB,
    office_subnet=DEFAULT_SUBNET,
    receiver_port=DEFAULT_PORT,
):
    """
    Render the Hioki Cell Sorting section.
    Compatible with Streamlit 1.52+ (uses width='stretch', no nested st.tabs).
    """
    try:
        db = _DB(db_path)
        on_office = _on_office_network(office_subnet)
        recv_up = _receiver_running(receiver_port)

        # ── Header ──────────────────────────────────────────────────────────
        st.markdown("## Battery Cell Sorting - Hioki BT3562A")

        col_net, col_recv, col_ref = st.columns([2, 2, 1])
        with col_net:
            if on_office:
                st.success("Office Network: Connected")
            else:
                st.error("Office Network: Not connected")
        with col_recv:
            if recv_up:
                st.success(f"Receiver port {receiver_port}: Running")
            else:
                st.warning(f"Receiver port {receiver_port}: Stopped")
        with col_ref:
            if st.button("Refresh", key="hioki_refresh"):
                st.rerun()

        if not recv_up:
            st.info(
                f"Start the receiver on the server: "
                f"`python hioki_simple_receiver.py --port {receiver_port}`"
            )

        st.markdown("---")

        # ── Navigation (radio instead of nested tabs) ────────────────────
        section = st.radio(
            "Section",
            ["Dashboard", "Add / Test", "History", "Reports"],
            horizontal=True,
            key="hioki_section",
            label_visibility="collapsed",
        )

        st.markdown("---")

        # ── Section content ──────────────────────────────────────────────
        if section == "Dashboard":
            _render_dashboard(db)
        elif section == "Add / Test":
            _render_add(db, on_office)
        elif section == "History":
            _render_history(db)
        elif section == "Reports":
            _render_reports(db)

        # ── Footer ──────────────────────────────────────────────────────
        st.markdown("---")
        col_inf, col_clr = st.columns(2)
        with col_inf:
            st.caption(f"Database: {Path(db_path).resolve()}")
            st.caption(
                f"Receiver port {receiver_port}: "
                f"{'running' if recv_up else 'stopped'} | "
                f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        with col_clr:
            if st.button("Clear All Data", key="hioki_clear"):
                if st.session_state.get("hioki_confirm_clear"):
                    try:
                        db.clear_all()
                        st.success("All data cleared.")
                        st.session_state["hioki_confirm_clear"] = False
                    except Exception as e:
                        st.error(f"Failed to clear: {e}")
                else:
                    st.session_state["hioki_confirm_clear"] = True
                    st.warning("Click Clear All Data again to confirm.")

    except Exception:
        st.error("Cell Sorting tab encountered an error:")
        st.code(traceback.format_exc())


# ---------------------------------------------------------------------------
# Standalone entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    st.set_page_config(page_title="Hioki Cell Sorting", layout="wide")
    render_hioki_cell_sorting_tab()
