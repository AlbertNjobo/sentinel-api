"""
app/metrics.py — system metrics helpers (psutil wrappers)
"""

import platform
import time
from datetime import datetime, timezone

import psutil

_START = time.time()


def uptime() -> float:
    return round(time.time() - _START, 2)


def health_snapshot() -> dict:
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    status = "healthy"
    if cpu > 90 or mem.percent > 90 or disk.percent > 95:
        status = "degraded"
    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime(),
        "checks": {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "disk_percent": disk.percent,
        },
    }


def full_metrics() -> dict:
    cpu_freq = psutil.cpu_freq()
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": {
            "hostname":     platform.node(),
            "os":           f"{platform.system()} {platform.release()}",
            "architecture": platform.machine(),
            "python":       platform.python_version(),
            "boot_time":    datetime.fromtimestamp(
                                psutil.boot_time(), tz=timezone.utc
                            ).isoformat(),
        },
        "cpu": {
            "percent":        psutil.cpu_percent(interval=0.2),
            "count_logical":  psutil.cpu_count(logical=True),
            "count_physical": psutil.cpu_count(logical=False),
            "frequency_mhz":  round(cpu_freq.current, 2) if cpu_freq else None,
            "per_core":       psutil.cpu_percent(percpu=True),
        },
        "memory": {
            "total_mb":      round(mem.total   / 1024**2, 2),
            "used_mb":       round(mem.used    / 1024**2, 2),
            "available_mb":  round(mem.available / 1024**2, 2),
            "percent":       mem.percent,
            "swap_total_mb": round(swap.total  / 1024**2, 2),
            "swap_used_mb":  round(swap.used   / 1024**2, 2),
            "swap_percent":  swap.percent,
        },
        "disk": {
            "total_gb": round(disk.total / 1024**3, 2),
            "used_gb":  round(disk.used  / 1024**3, 2),
            "free_gb":  round(disk.free  / 1024**3, 2),
            "percent":  disk.percent,
        },
        "network": {
            "bytes_sent":    net.bytes_sent,
            "bytes_recv":    net.bytes_recv,
            "packets_sent":  net.packets_sent,
            "packets_recv":  net.packets_recv,
            "errin":         net.errin,
            "errout":        net.errout,
        },
    }


def top_processes(limit: int = 10) -> dict:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_processes": len(procs),
        "top": procs[:limit],
    }
