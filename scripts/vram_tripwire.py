#!/usr/bin/env python3
"""VRAM tripwire — SIGKILL the ComfyUI process the instant GPU VRAM crosses a ceiling.

On this 24 GB RTX 3090 (which also drives the desktop), a transient VRAM spike to the
physical ceiling wedges the GPU and freezes the whole machine (hard reset required).
1 Hz nvidia-smi polling misses sub-second spikes; this binds NVML directly via ctypes
(no pip dependency, sub-millisecond reads) to poll at high frequency, kill before the
ceiling is reached, and log the running peak — so it doubles as the instrument that
finally shows where VRAM actually peaks.

A tripwire is REACTIVE: it cannot preempt a single instantaneous allocation that jumps
straight past the ceiling between two polls. Pair it with ComfyUI's --reserve-vram, which
fails such an allocation gracefully in-process. This guard catches climbing spikes and is
the safety net + instrument; --reserve-vram is the prevention.

Usage:
    vram_tripwire.py [--ceil-mb 21000] [--match "main.py --listen"] [--hz 200]
                     [--log /tmp/vram_tripwire.log]
"""
import argparse
import ctypes
import os
import signal
import sys
import time


class _Mem(ctypes.Structure):
    _fields_ = [("total", ctypes.c_ulonglong),
                ("free", ctypes.c_ulonglong),
                ("used", ctypes.c_ulonglong)]


def nvml_open():
    lib = ctypes.CDLL("libnvidia-ml.so.1")
    if lib.nvmlInit_v2() != 0:
        sys.exit("nvmlInit failed")
    handle = ctypes.c_void_p()
    if lib.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle)) != 0:
        sys.exit("nvmlDeviceGetHandleByIndex failed")
    return lib, handle


def used_mb(lib, handle):
    m = _Mem()
    lib.nvmlDeviceGetMemoryInfo(handle, ctypes.byref(m))
    return m.used / 1048576.0


def mem_available_mb():
    """System RAM available (MB) from /proc/meminfo — the resource that actually freezes this rig."""
    with open("/proc/meminfo") as fh:
        for line in fh:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024.0
    return float("inf")


def find_pid(match):
    """Newest PID whose cmdline contains `match` (excluding this guard)."""
    best = None
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as fh:
                cmd = fh.read().replace(b"\0", b" ").decode("utf-8", "ignore")
        except OSError:
            continue
        if match in cmd and "vram_tripwire" not in cmd:
            best = int(pid)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ceil-mb", type=int, default=21000,
                    help="kill the target when VRAM used reaches this (leaves headroom for the display)")
    ap.add_argument("--ram-floor-mb", type=int, default=4000,
                    help="kill the target when system RAM available drops below this (prevents the freeze)")
    ap.add_argument("--match", default="main.py --listen",
                    help="cmdline substring identifying the process to kill (ComfyUI)")
    ap.add_argument("--hz", type=float, default=200.0, help="poll frequency")
    ap.add_argument("--log", default="/tmp/vram_tripwire.log")
    a = ap.parse_args()

    lib, handle = nvml_open()
    period = 1.0 / a.hz
    peak = 0.0
    logf = open(a.log, "a", buffering=1)

    def emit(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        logf.write(line + "\n")

    emit(f"[tripwire] ARMED  vram_ceil={a.ceil_mb}MB  ram_floor={a.ram_floor_mb}MB  match='{a.match}'  hz={a.hz:g}")
    last_report = 0.0
    ram_low = float("inf")
    while True:
        u = used_mb(lib, handle)
        ram = mem_available_mb()
        if u > peak:
            peak = u
        if ram < ram_low:
            ram_low = ram
        now = time.time()
        if now - last_report >= 1.0:
            emit(f"[tripwire] vram={u:.0f}MB (peak {peak:.0f})  ram_avail={ram:.0f}MB (low {ram_low:.0f})")
            last_report = now
        trip = None
        if u >= a.ceil_mb:
            trip = f"VRAM {u:.0f}MB >= ceil {a.ceil_mb}MB"
        elif ram <= a.ram_floor_mb:
            trip = f"RAM avail {ram:.0f}MB <= floor {a.ram_floor_mb}MB"
        if trip:
            pid = find_pid(a.match)
            emit(f"[tripwire] !!! {trip} — KILLING pid {pid} (vram peak {peak:.0f}MB, ram low {ram_low:.0f}MB)")
            if pid:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError as exc:
                    emit(f"[tripwire] kill failed: {exc}")
            emit("[tripwire] killed; draining 2s then re-arming")
            time.sleep(2.0)
            peak = 0.0
            ram_low = float("inf")
        time.sleep(period)


if __name__ == "__main__":
    main()
