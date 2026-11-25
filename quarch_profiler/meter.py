"""The Quarch meter, reached through quarchpy and QIS."""

import atexit
import re
import time

from quarchpy.device import get_quarch_device
from quarchpy.qis import QisInterface, isQisRunning, startLocalQis

from .settings import CONNECT_TIMEOUT, DEVICE, DRAIN_STALL_SECONDS


class QuarchMeter:
    """One Quarch meter: connect, start a recording, stop it, read the samples back.

        meter = QuarchMeter("USB::QTL2843-03-023")
        meter.start_recording()
        ...                                  # the code being measured
        raw = meter.stop_recording()         # every sample, as text

    The connection is opened on first use (QIS is started if it is not running)
    and closed by close() or when Python exits. Only one recording can run at a
    time, because the meter has a single stream.
    """

    def __init__(self, device=DEVICE, connect_timeout=CONNECT_TIMEOUT):
        self._device = device
        self.connect_timeout = connect_timeout  # seconds QIS may take to find the meter
        self._dev = None                # quarchpy device, None until connected
        self._recording = False
        atexit.register(self.close)

    # ------------------------------------------------------------------ info

    @staticmethod
    def list_devices():
        """Devices QIS can see, as connection strings, e.g. ["USB::QTL2843-03-023"].
        Starts QIS if it is not running."""
        if not isQisRunning():
            startLocalQis()
        qis = QisInterface(connectionMessage=False)
        try:
            lines = list(qis.get_device_list())
        finally:
            qis.disconnect()
        devices = []
        for line in lines:
            # QIS numbers the list ("1) USB::QTL2843-03-023"); keep only the name.
            name = re.sub(r"^\s*\d+\)\s*", "", line).strip()
            if name and "no devices" not in name.lower():
                devices.append(name)
        return devices

    @property
    def device(self):
        return self._device

    @device.setter
    def device(self, name):
        if self.connected:
            raise RuntimeError(f"already connected to {self._device} - call close() first")
        self._device = name

    @property
    def connected(self):
        return self._dev is not None

    @property
    def recording(self):
        return self._recording

    # ------------------------------------------------------------ connection

    def connect(self):
        """Open the connection if it is not open yet. Returns the quarchpy device."""
        if self._dev is None:
            if not isQisRunning():
                startLocalQis()
            self._dev = get_quarch_device(self._device, ConType="QIS",
                                          timeout=str(self.connect_timeout))
            print(f"[quarch_profiler] connected to {self._device}", flush=True)
        return self._dev

    def close(self):
        if self._dev is not None:
            try:
                self._dev.close_connection()
            finally:
                self._dev = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    # ------------------------------------------------------------- recording

    def start_recording(self):
        if self._recording:
            raise RuntimeError("a Quarch recording is already running - recordings cannot nest")
        self._check_ok("rec stream", self.connect().send_command("rec stream"))
        self._recording = True

    def stop_recording(self):
        """Stop the recording and return all of its samples as text."""
        try:
            self._check_ok("rec stop", self.connect().send_command("rec stop"))
            return self._read_all_data()
        finally:
            self._recording = False

    def abort_recording(self):
        """Stop the recording and throw its samples away, so the next recording
        does not start with stale data. Never raises."""
        try:
            self.connect().send_command("rec stop")
            self._read_all_data()
        except Exception:
            pass
        finally:
            self._recording = False

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _check_ok(command, reply):
        """Raise if the meter did not answer OK (e.g. "FAIL: 0x47", "Connection Timeout")."""
        if reply.strip() != "OK":
            raise RuntimeError(f"meter replied {reply.strip()!r} to {command!r} - "
                               "it may be stuck; restart QIS / reset the meter")

    def _read_all_data(self):
        """Read the stopped recording from QIS. Returns once QIS reports the stream
        stopped AND every buffered sample has been handed over ("stoppedeof")."""
        qis = self.connect().connectionObj.qis
        chunks = []
        last_data = time.monotonic()
        while True:
            status, text = qis.stream_get_stripes_text(qis.sock, self._device)
            chunks.append(text)
            if "overrun" in status:
                raise RuntimeError("QIS buffer overrun - data was lost")
            if "eof" in status:
                return "".join(chunks)
            # quarchpy reports any unrecognised reply as "running", so without
            # this check a stuck meter makes the loop spin forever.
            if text[:1].isdigit():          # data rows start with the timestamp
                last_data = time.monotonic()
            elif time.monotonic() - last_data > DRAIN_STALL_SECONDS:
                raise RuntimeError(f"no data from the meter for {DRAIN_STALL_SECONDS} s "
                                   f"(last reply {text.strip()[:80]!r}) - it may be stuck; "
                                   "restart QIS / reset the meter")
