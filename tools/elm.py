#!/usr/bin/env python3
"""Read-only ELM327 diagnostic helper for Haval Dargo research.

Only reading commands are allowed to reach the car (see ALLOWED_* below).
Everything sent/received is logged to logs/elm-<timestamp>.log.

Transports:
  --port /dev/cu.XXX   classic Bluetooth (SPP) or USB adapter
  --port socket://192.168.0.10:35000   Wi-Fi adapter
  --ble [NAME|ADDR]    BLE adapter (auto-detects notify/write characteristics)

Commands: ports, ble-scan, info, obd, monitor, scan11, scan29, read-ids, dtc, raw
"""
import argparse
import asyncio
import datetime as dt
import pathlib
import re
import sys

LOG_DIR = pathlib.Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG = open(LOG_DIR / f"elm-{dt.datetime.now():%Y%m%d-%H%M%S}.log", "a", buffering=1)


def log(line):
    stamp = dt.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    LOG.write(f"{stamp} {line}\n")


# ---- safety whitelist ------------------------------------------------------
# UDS: 0x3E TesterPresent, 0x22 ReadDataByIdentifier, 0x19 ReadDTCInformation
ALLOWED_UDS = {0x3E, 0x22, 0x19}
# OBD-II modes: 01 live data, 03 stored DTC, 07 pending DTC, 09 vehicle info
ALLOWED_OBD = {0x01, 0x03, 0x07, 0x09}
# AT commands that change only adapter state (never the car)
BLOCKED_AT = ("ATPP", "ATWS")  # programmable params / warm start not needed


def check_safe(cmd):
    c = cmd.replace(" ", "").upper()
    if c.startswith("AT") or c.startswith("ST"):
        if c.startswith(BLOCKED_AT):
            raise ValueError(f"blocked adapter command: {cmd}")
        return
    if not re.fullmatch(r"[0-9A-F]{2,}", c):
        raise ValueError(f"not hex: {cmd}")
    sid = int(c[:2], 16)
    if sid in ALLOWED_UDS or sid in ALLOWED_OBD:
        return
    raise ValueError(f"service 0x{sid:02X} is not read-only, refused: {cmd}")


# ---- transports ------------------------------------------------------------
class SerialT:
    def __init__(self, port):
        import serial
        # accepts /dev/cu.XXX or socket://192.168.0.10:35000 for Wi-Fi adapters
        self.s = serial.serial_for_url(port, 38400, timeout=0.1)

    async def write(self, data: bytes):
        await asyncio.to_thread(self.s.write, data)

    async def read_some(self) -> bytes:
        return await asyncio.to_thread(self.s.read, 256)

    async def close(self):
        self.s.close()


class BleT:
    def __init__(self, client, wchar, nchar):
        self.c, self.w, self.n = client, wchar, nchar
        self.q = asyncio.Queue()

    @classmethod
    async def connect(cls, target):
        from bleak import BleakClient, BleakScanner
        dev = None
        if target and re.fullmatch(r"[0-9A-Fa-f:-]{17,36}", target):
            dev = await BleakScanner.find_device_by_address(target, timeout=10)
        else:
            want = (target or "").lower()
            for d in await BleakScanner.discover(timeout=8):
                name = (d.name or "").lower()
                if (want and want in name) or (not want and any(
                        k in name for k in ("obd", "elm", "vlink", "vgate", "icar", "v-link", "ios"))):
                    dev = d
                    break
        if not dev:
            raise SystemExit("BLE adapter not found; run `ble-scan` and pass --ble <name or address>")
        client = BleakClient(dev)
        await client.connect()
        wchar = nchar = None
        for svc in client.services:
            for ch in svc.characteristics:
                p = ch.properties
                if nchar is None and ("notify" in p or "indicate" in p):
                    nchar = ch
                if wchar is None and ("write" in p or "write-without-response" in p):
                    wchar = ch
        if not (wchar and nchar):
            raise SystemExit("could not find write/notify characteristics")
        log(f"BLE {dev.name} {dev.address} write={wchar.uuid} notify={nchar.uuid}")
        t = cls(client, wchar, nchar)
        await client.start_notify(nchar, lambda _, d: t.q.put_nowait(bytes(d)))
        return t

    async def write(self, data: bytes):
        resp = "write" in self.w.properties
        for i in range(0, len(data), 20):
            await self.c.write_gatt_char(self.w, data[i:i + 20], response=resp)

    async def read_some(self) -> bytes:
        try:
            return await asyncio.wait_for(self.q.get(), 0.1)
        except asyncio.TimeoutError:
            return b""

    async def close(self):
        await self.c.disconnect()


# ---- ELM protocol ----------------------------------------------------------
class Elm:
    def __init__(self, t):
        self.t = t

    async def cmd(self, c, timeout=3.0, quiet=False):
        check_safe(c)
        log(f">> {c}")
        await self.t.write((c + "\r").encode())
        buf = b""
        loop = asyncio.get_running_loop()
        end = loop.time() + timeout
        while loop.time() < end:
            buf += await self.t.read_some()
            if b">" in buf:
                break
        text = buf.decode(errors="replace").replace(">", "")
        lines = [l.strip() for l in re.split(r"[\r\n]+", text) if l.strip() and l.strip() != c]
        for l in lines:
            log(f"<< {l}")
        if not quiet:
            print(f"{c:<14} -> {' | '.join(lines) if lines else '(no answer)'}")
        return lines

    async def init(self):
        for c in ("ATZ", "ATE0", "ATL0", "ATS1", "ATH1", "ATSP0"):
            await self.cmd(c, timeout=4, quiet=True)
        print("adapter:", " ".join(await self.cmd("ATI", quiet=True)))

    async def monitor(self, seconds):
        await self.cmd("ATH1", quiet=True)
        await self.cmd("ATCAF0", quiet=True)
        log(">> ATMA")
        await self.t.write(b"ATMA\r")
        loop = asyncio.get_running_loop()
        end, buf, frames = loop.time() + seconds, b"", 0
        while loop.time() < end:
            buf += await self.t.read_some()
            *done, buf = re.split(rb"[\r\n]+", buf)
            for l in done:
                s = l.decode(errors="replace").strip()
                if s:
                    frames += 1
                    log(f"<< {s}")
                    if frames <= 40:
                        print(s)
        await self.t.write(b"\r")  # any char stops monitoring
        await asyncio.sleep(0.5)
        while await self.t.read_some():
            pass
        await self.cmd("ATCAF1", quiet=True)
        print(f"--- {frames} frames in {seconds}s (full list in log)")


def responders(lines, tx_hdr):
    out = {}
    for l in lines:
        parts = l.split()
        if len(parts) >= 3 and re.fullmatch(r"[0-9A-F]{3}|[0-9A-F]{8}", parts[0]) and parts[0] != tx_hdr:
            out.setdefault(parts[0], []).append(" ".join(parts[1:]))
    return out


async def scan11(e, lo, hi):
    for c in ("ATSP6", "ATH1", "ATCAF1", "ATST19", "ATCF700", "ATCM700"):
        await e.cmd(c, quiet=True)
    found = {}
    for tx in range(lo, hi + 1):
        if tx == 0x7DF:
            continue
        h = f"{tx:03X}"
        await e.cmd(f"ATSH{h}", quiet=True)
        r = responders(await e.cmd("3E00", timeout=0.6, quiet=True), h)
        if r:
            found[h] = r
            print(f"tx {h}: {r}")
    await e.cmd("ATCRA", quiet=True)
    print(f"=== 11-bit scan done, {len(found)} responders")
    return found


async def scan29(e):
    for c in ("ATSP7", "ATH1", "ATCAF1", "ATST19", "ATCF18DAF100", "ATCM1FFFFF00"):
        await e.cmd(c, quiet=True)
    found = {}
    for tgt in range(0x100):
        h = f"18DA{tgt:02X}F1"
        await e.cmd(f"ATSH{h[2:]}", quiet=True)
        await e.cmd("ATCP18", quiet=True)
        r = responders(await e.cmd("3E00", timeout=0.6, quiet=True), h)
        if r:
            found[h] = r
            print(f"tx {h}: {r}")
    print(f"=== 29-bit scan done, {len(found)} responders")
    return found


DIDS = {
    "F187": "spare part number", "F18A": "supplier id", "F18C": "serial",
    "F190": "VIN", "F191": "hw number", "F193": "hw version",
    "F195": "sw version", "F197": "system name",
}


def ascii_of(lines):
    data = []
    for l in lines:
        p = l.split()[1:]
        if p and re.fullmatch(r"[0-9A-F]{2}", p[0]):
            data += p
    try:
        return bytes(int(x, 16) for x in data).decode("ascii", "replace")
    except ValueError:
        return ""


async def address(e, tx, rx):
    ext = len(tx) > 3
    for c in ("ATSP7" if ext else "ATSP6", "ATH1", "ATCAF1", "ATST64"):
        await e.cmd(c, quiet=True)
    if ext:
        await e.cmd(f"ATCP{tx[:2]}", quiet=True)
        await e.cmd(f"ATSH{tx[2:]}", quiet=True)
    else:
        await e.cmd(f"ATSH{tx}", quiet=True)
    await e.cmd(f"ATCRA{rx}", quiet=True)


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port")
    ap.add_argument("--ble", nargs="?", const="")
    sp = ap.add_subparsers(dest="what", required=True)
    sp.add_parser("ports")
    sp.add_parser("ble-scan")
    sp.add_parser("info")
    sp.add_parser("obd")
    m = sp.add_parser("monitor"); m.add_argument("--seconds", type=int, default=10)
    s = sp.add_parser("scan11"); s.add_argument("--lo", default="700"); s.add_argument("--hi", default="7FF")
    sp.add_parser("scan29")
    for name in ("read-ids", "dtc"):
        p = sp.add_parser(name); p.add_argument("--tx", required=True); p.add_argument("--rx", required=True)
    r = sp.add_parser("raw"); r.add_argument("cmds", nargs="+")
    a = ap.parse_args()

    if a.what == "ports":
        from serial.tools import list_ports
        for p in list_ports.comports():
            print(p.device, "-", p.description)
        return
    if a.what == "ble-scan":
        from bleak import BleakScanner
        for d in await BleakScanner.discover(timeout=8):
            print(d.address, d.name)
        return

    if a.port:
        t = SerialT(a.port)
    elif a.ble is not None:
        t = await BleT.connect(a.ble)
    else:
        sys.exit("pass --port /dev/cu.XXX or --ble [name]")
    e = Elm(t)
    print("log:", LOG.name)
    try:
        await e.init()
        if a.what == "info":
            for c in ("ATRV", "0100", "ATDP", "ATDPN"):
                await e.cmd(c, timeout=8)
        elif a.what == "obd":
            for c in ("0100", "0902", "03", "07", "0105", "010C"):
                await e.cmd(c, timeout=8)
        elif a.what == "monitor":
            await e.monitor(a.seconds)
        elif a.what == "scan11":
            await scan11(e, int(a.lo, 16), int(a.hi, 16))
        elif a.what == "scan29":
            await scan29(e)
        elif a.what == "read-ids":
            await address(e, a.tx.upper(), a.rx.upper())
            for did, label in DIDS.items():
                lines = await e.cmd("22" + did, timeout=2, quiet=True)
                print(f"{did} {label:<18} {' | '.join(lines)}  {ascii_of(lines)!r}")
        elif a.what == "dtc":
            await address(e, a.tx.upper(), a.rx.upper())
            await e.cmd("1902FF", timeout=3)
        elif a.what == "raw":
            for c in a.cmds:
                await e.cmd(c, timeout=5)
    finally:
        await t.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ValueError as err:
        sys.exit(f"REFUSED: {err}")
