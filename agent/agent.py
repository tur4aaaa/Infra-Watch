import logging
import os
import shutil
import socket
import time

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SAMPLE_INTERVAL = float(os.getenv("INFRAWATCH_SAMPLE_INTERVAL", "1"))
NETWORK_INTERFACES = [
    n.strip() for n in os.getenv("INFRAWATCH_NET_INTERFACES", "").split(",") if n.strip()
]


def get_memory():
    memory = {}
    with open("/proc/meminfo") as file:
        for line in file:
            key, value = line.split(":", 1)
            memory[key] = int(value.strip().split()[0])

    total = memory["MemTotal"]
    available = memory["MemAvailable"]
    used = total - available
    return {
        "total_kb": total,
        "available_kb": available,
        "used_kb": used,
        "used_percent": round(used / total * 100, 2),
    }


def get_cpu_times():
    # user nice system idle iowait irq softirq steal (guest уже входит в user)
    with open("/proc/stat") as file:
        values = [int(v) for v in file.readline().split()[1:]]
    user, nice, system, idle, iowait, irq, softirq, steal = (values + [0] * 8)[:8]
    idle_all = idle + iowait
    total = user + nice + system + idle_all + irq + softirq + steal
    return total, idle_all


def get_disk_usage(path="/"):
    total, used, free = shutil.disk_usage(path)
    usable = used + free  # как в df: зарезервированные блоки не считаем
    return {
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": free,
        "used_percent": round(used / usable * 100, 2) if usable else 0.0,
    }


def get_network_counters():
    rx_total = tx_total = 0
    with open("/proc/net/dev") as file:
        for line in file:
            if ":" not in line:
                continue
            interface, data = line.split(":", 1)
            interface = interface.strip()
            if NETWORK_INTERFACES:
                if interface not in NETWORK_INTERFACES:
                    continue
            elif interface == "lo":
                continue
            values = data.split()
            rx_total += int(values[0])
            tx_total += int(values[8])
    return rx_total, tx_total


def get_hostname():
    return socket.gethostname()


def get_uptime_seconds():
    with open("/proc/uptime") as file:
        return int(float(file.readline().split()[0]))


def collect_system_metrics():
    cpu_total_1, cpu_idle_1 = get_cpu_times()
    rx_1, tx_1 = get_network_counters()

    time.sleep(SAMPLE_INTERVAL)

    cpu_total_2, cpu_idle_2 = get_cpu_times()
    rx_2, tx_2 = get_network_counters()

    total_delta = cpu_total_2 - cpu_total_1
    idle_delta = cpu_idle_2 - cpu_idle_1
    cpu_usage = (total_delta - idle_delta) / total_delta * 100 if total_delta else 0.0

    return {
        "hostname": get_hostname(),
        "timestamp": int(time.time()),
        "uptime_seconds": get_uptime_seconds(),
        "cpu_usage": round(cpu_usage, 2),
        "memory": get_memory(),
        "disk": get_disk_usage(),
        "network": {
            "rx_bytes_per_sec": round((rx_2 - rx_1) / SAMPLE_INTERVAL),
            "tx_bytes_per_sec": round((tx_2 - tx_1) / SAMPLE_INTERVAL),
        },
    }


if __name__ == "__main__":
    m = collect_system_metrics()
    logger.info("System metrics for %s:", m["hostname"])
    logger.info("  CPU:     %.2f%%", m["cpu_usage"])
    logger.info("  Memory:  %.2f%%", m["memory"]["used_percent"])
    logger.info("  Disk:    %.2f%%", m["disk"]["used_percent"])
    logger.info("  Uptime:  %d s", m["uptime_seconds"])
    logger.info("  Network: RX = %.2f KB/s | TX = %.2f KB/s",
                m["network"]["rx_bytes_per_sec"] / 1024,
                m["network"]["tx_bytes_per_sec"] / 1024)