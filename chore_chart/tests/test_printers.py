import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "app"))

from server import parse_browse  # noqa: E402

# `avahi-browse --resolve --parsable --terminate _ipp._tcp` lines in the real format, with made-up printers.
OUTPUT = "\n".join([
    "+;wlan0;IPv4;Hall\\032Printer;Internet Printer;local",
    "=;wlan0;IPv6;Hall\\032Printer;Internet Printer;local;printer-1.local;fe80::1;631;"
    '"rp=ipp/print" "ty=Example Inkjet 100"',
    "=;wlan0;IPv4;Hall\\032Printer;Internet Printer;local;printer-1.local;192.168.1.50;631;"
    '"txtvers=1" "qtotal=1" "rp=ipp/print" "note=" "ty=Example Inkjet 100" "priority=25"',
    "=;eth0;IPv4;ChoreSim;Internet Printer;local;sim.local;172.28.5.20;8631;\"rp=ipp/print\"",
])


class ParseBrowseTest(unittest.TestCase):
    def test_keeps_resolved_ipv4_and_unescapes_names(self):
        self.assertEqual(parse_browse(OUTPUT), {
            "Hall Printer": {"model": "Example Inkjet 100", "address": "ipp://192.168.1.50:631/ipp/print"},
            "ChoreSim": {"model": "", "address": "ipp://172.28.5.20:8631/ipp/print"},
        })

    def test_nothing_found(self):
        self.assertEqual(parse_browse(""), {})


if __name__ == "__main__":
    unittest.main()
