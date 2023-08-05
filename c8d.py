import machine, time
from struct import pack

_C8D_READ_PPM = b'\x64\x69\x03\x5e\x4e'
_C8D_SINGLE_POINT_CALIB = b'\x11\x03\x03'  # followed by data1, data2, checksum

_C8D_MIN_VALUE = 0
_C8D_MAX_VALUE = 5000

class C8D:
    def __init__(self, uart_id, baudrate=9600, refresh_rate=3000):
        self._uart = machine.UART(uart_id, baudrate=baudrate)
        self._buf = bytearray(14)

        self._last_reading = 0
        self._refresh_rate = max(refresh_rate, 1000)
        self._read()

    def calibrate(self, ppm) -> None:
        ppm = max(min(ppm, 1500), 400)  # ppm must be in range 400-1500
        lo, hi = int(ppm % 256), int(ppm / 256)
        query = _C8D_SINGLE_POINT_CALIB + pack('b', hi) + pack('b', lo)
        query += pack('b', sum(query))

        self._uart.write(query)
        time.sleep_ms(2)
        self._uart.readinto(self._buf)
        time.sleep(10)
        b = bytearray(4)
        self._uart.readinto(b)  # expect \x16\x01\x03\xe6
        print(b)
        self._read()  # read out leftover pre-calibration data

    def _read(self) -> None:
        if (time.ticks_diff(self._last_reading, time.ticks_ms()) * time.ticks_diff(0, 1) < self._refresh_rate):
            return

        self._uart.write(_C8D_READ_PPM)
        time.sleep_ms(2)
        self._uart.readinto(self._buf)
        self._last_reading = time.ticks_ms()

    @property
    def co2(self) -> float:
        self._read()
        return int(self._buf[5])*256.0 + int(self._buf[4])

