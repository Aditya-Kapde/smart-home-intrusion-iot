"""Host network monitoring for ShieldHome.

This module samples network connection metadata and traffic counters
using psutil and writes notable observations into events.json.
"""

from __future__ import annotations

import ipaddress
import os
import threading
import time
from datetime import datetime

import psutil

from storage import save_event

COMMON_REMOTE_PORTS = {
    20, 21, 22, 25, 53, 67, 68, 80, 110, 123, 143, 389, 443, 587, 993, 995,
    3306, 5432, 6379, 27017,
}


def _parse_port_set(value: str) -> set[int]:
    ports: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ports.add(int(part))
        except ValueError:
            continue
    return ports


def _is_external_ip(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return not (ip.is_loopback or ip.is_private or ip.is_link_local)


class NetworkMonitor:
    def __init__(self) -> None:
        self.interval = max(5, int(os.getenv("NETWORK_MONITOR_INTERVAL", "15")))
        self.burst_bytes = max(100_000, int(os.getenv("NETWORK_BURST_BYTES", "500000")))
        self.suspicious_ports = _parse_port_set(
            os.getenv("NETWORK_SUSPICIOUS_PORTS", "23,2323,3389,4444,5555,6667,7777,8081,9001")
        )
        self.monitored_ports = _parse_port_set(
            os.getenv("NETWORK_MONITORED_PORTS", "5000,8050")
        )
        self._last_counters = psutil.net_io_counters()
        self._seen_connections: set[tuple] = set()
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, name="NetworkMonitor", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while self._running:
            try:
                self.sample()
            except Exception as exc:
                save_event({
                    "source": "Network Monitor",
                    "event_class": "network",
                    "network_type": "error",
                    "intrusion": False,
                    "message": f"Network monitor error: {exc}",
                })
            time.sleep(self.interval)

    def sample(self) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        counters = psutil.net_io_counters()
        sent_delta = max(0, counters.bytes_sent - self._last_counters.bytes_sent)
        recv_delta = max(0, counters.bytes_recv - self._last_counters.bytes_recv)
        self._last_counters = counters

        active_connections = []
        suspicious_hits = 0

        for conn in psutil.net_connections(kind="inet"):
            if not conn.raddr or conn.status not in {psutil.CONN_ESTABLISHED, psutil.CONN_LISTEN}:
                continue

            local_port = getattr(conn.laddr, "port", None)
            remote_ip = getattr(conn.raddr, "ip", "")
            remote_port = getattr(conn.raddr, "port", None)
            key = (
                getattr(conn.laddr, "ip", ""),
                local_port,
                remote_ip,
                remote_port,
                conn.status,
                conn.pid,
            )
            active_connections.append(key)

            if key in self._seen_connections:
                continue

            self._seen_connections.add(key)

            is_internal_service = remote_port in self.monitored_ports
            is_suspicious = remote_port in self.suspicious_ports or _is_external_ip(remote_ip)

            if is_internal_service or is_suspicious:
                if is_suspicious:
                    suspicious_hits += 1
                save_event({
                    "timestamp": now,
                    "source": "Network Monitor",
                    "event_class": "network",
                    "network_type": "connection",
                    "intrusion": False,
                    "severity": "warning" if is_suspicious else "info",
                    "message": (
                        f"New network connection to {remote_ip}:{remote_port} from local port {local_port}"
                        if is_suspicious
                        else f"Internal service connection to {remote_ip}:{remote_port}"
                    ),
                    "local_port": local_port,
                    "remote_ip": remote_ip,
                    "remote_port": remote_port,
                    "status": conn.status,
                })

        if sent_delta >= self.burst_bytes or recv_delta >= self.burst_bytes:
            save_event({
                "timestamp": now,
                "source": "Network Monitor",
                "event_class": "network",
                "network_type": "traffic",
                "intrusion": False,
                "severity": "info",
                "message": (
                    f"High network activity detected: +{sent_delta} bytes sent, +{recv_delta} bytes received"
                ),
                "active_connections": len(active_connections),
            })

        if suspicious_hits == 0 and not active_connections:
            save_event({
                "timestamp": now,
                "source": "Network Monitor",
                "event_class": "network",
                "network_type": "summary",
                "intrusion": False,
                "severity": "info",
                "message": "Network monitor snapshot recorded — no active external connections.",
                "active_connections": 0,
                "bytes_sent": sent_delta,
                "bytes_received": recv_delta,
            })


_monitor: NetworkMonitor | None = None


def start_network_monitor() -> None:
    global _monitor
    if _monitor is None:
        _monitor = NetworkMonitor()
        _monitor.start()