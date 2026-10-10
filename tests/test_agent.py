from unittest.mock import mock_open, patch

from agent import agent


# MEMORY

MEMINFO = """\
MemTotal:       16000000 kB
MemFree:         2000000 kB
MemAvailable:   12000000 kB
Buffers:          500000 kB
"""

def test_get_memory():
    with patch("builtins.open", mock_open(read_data=MEMINFO)):
        memory = agent.get_memory()

    assert memory["total_kb"] == 16000000
    assert memory["available_kb"] == 12000000
    assert memory["used_kb"] == 4000000
    assert memory["used_percent"] == 25.0

#CPU

PROC_STAT = "cpu  100 0 50 800 50 0 0 0 0 0\ncpu0 50 0 25 400 25 0 0 0 0 0\n"

def test_iowait_counts_as_idle():
    with patch("builtins.open", mock_open(read_data=PROC_STAT)):
        total,idle = agent.get_cpu_times()

    assert idle == 850
    assert total == 1000

def test_cpu_usage_from_two_snapshots(monkeypatch):
    # Two snapshots of CPU times: (total, idle)
    snapshots = iter([(1000, 850), (1100, 900)])
    monkeypatch.setattr(agent, "get_cpu_times", lambda: next(snapshots))
    monkeypatch.setattr(agent, "get_network_counters", lambda: (0, 0))
    monkeypatch.setattr(agent.time, "sleep", lambda seconds: None)  # не ждём реальную секунду

    metrics = agent.collect_system_metrics()

    assert metrics["cpu_usage"] == 50.0

def test_cpu_usage_when_no_time_passed(monkeypatch):
    # No division by zero error when no time has passed
    monkeypatch.setattr(agent, "get_cpu_times", lambda: (1000, 850))
    monkeypatch.setattr(agent, "get_network_counters", lambda: (0, 0))
    monkeypatch.setattr(agent.time, "sleep", lambda seconds: None)

    metrics = agent.collect_system_metrics()

    assert metrics["cpu_usage"] == 0.0


# NETWORK
NET_DEV = """\
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo:  1000 10 0 0 0 0 0 0  1000 10 0 0 0 0 0 0
  eth0:  5000 50 0 0 0 0 0 0  3000 30 0 0 0 0 0 0
 wlan0:   200  2 0 0 0 0 0 0   100  1 0 0 0 0 0 0
"""


def test_network_sums_all_interfaces_except_loopback(monkeypatch):
    monkeypatch.setattr(agent, "NETWORK_INTERFACES", [])
    with patch("builtins.open", mock_open(read_data=NET_DEV)):
        rx, tx = agent.get_network_counters()

    assert rx == 5200   # eth0 + wlan0, not lo
    assert tx == 3100


def test_network_only_selected_interfaces(monkeypatch):
    monkeypatch.setattr(agent, "NETWORK_INTERFACES", ["eth0"])
    with patch("builtins.open", mock_open(read_data=NET_DEV)):
        rx, tx = agent.get_network_counters()

    assert (rx, tx) == (5000, 3000)
    