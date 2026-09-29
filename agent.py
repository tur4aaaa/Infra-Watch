import time
import logging
import shutil

from pyparsing import line


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


def get_memory():
    with open("/proc/meminfo") as file:
        lines = file.readlines()

    memory = {}

    for line in lines: #Checking every line in the file and splitting it into key and value
        key, value = line.split(":")
        memory[key] = int(value.strip().split()[0])

    total = memory["MemTotal"]
    available = memory["MemAvailable"]
    used = total - available
    used_percent = used / total * 100

    return {
        "total_kb": total,
        "available_kb": available,
        "used_kb": used,
        "used_percent": round(used_percent, 2),
    }
def get_cpu_usage():
    with open("/proc/stat") as file:
        line = file.readline()

    values = line.split()[1:]

    user = int(values[0])
    system = int(values[2])
    idle = int(values[3])

    total = user + system + idle

    return total,idle

def calculate_cpu_usage(): # In order to get the CPU usage, we need to get the total and Idle CPU times two times and calculate the difference between time.Cause command /proc/stat return values since boot. I just did it by myself,maybe there are another way to do it,
    total_1, idle_1 = get_cpu_usage()

    time.sleep(1)

    total_2, idle_2 = get_cpu_usage()

    total_delta = total_2 - total_1
    idle_delta = idle_2 - idle_1

    usage = (total_delta - idle_delta) / total_delta * 100

    return round(usage, 2)

def get_disk_usage():
    total,used,free = shutil.disk_usage("/")

    used_percent = used / total * 100 #Qiet the same as we did with memory and CPU usage.

    return {
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": free,
        "used_percent": round(used_percent, 2),
    }

def get_network_counters():
    with open("/proc/net/dev") as file:
        lines = file.readlines()

    target_interface = "wlx58044f6cd386"

    for line in lines:
        line = line.strip()

        if ":" not in line:
            continue

        interface, data = line.split(":", 1)
        interface = interface.strip()

        if interface != target_interface:
            continue

        values = data.split()

        rx_bytes = int(values[0])
        tx_bytes = int(values[8])

        return rx_bytes, tx_bytes

def calculate_network_speed():
    rx_1, tx_1 = get_network_counters()

    time.sleep(1)

    rx_2, tx_2 = get_network_counters() #Get the network counters two times and calculate the difference between them to get the speed in bytes per second.

    rx_speed = rx_2 - rx_1
    tx_speed = tx_2 - tx_1

    return rx_speed, tx_speed

def collect_system_metrics():
    memory = get_memory()
    cpu_usage = calculate_cpu_usage()
    disk = get_disk_usage()

    rx, tx = calculate_network_speed()

    return {
        "memory": memory,
        "cpu_usage": cpu_usage,
        "disk": disk,
        "network": {
            "rx_speed": rx,
            "tx_speed": tx,
        },
    }

metrics = collect_system_metrics()

logger.info("System metrics:")
logger.info("  CPU:    %.2f%%", metrics["cpu_usage"])
logger.info("  Memory: %.2f%%", metrics["memory"]["used_percent"])
logger.info("  Disk:   %.2f%%", metrics["disk"]["used_percent"])
logger.info(
    "  Network: RX=%d bytes/s | TX=%d bytes/s",
    metrics["network"]["rx_speed"],
    metrics["network"]["tx_speed"],
)

