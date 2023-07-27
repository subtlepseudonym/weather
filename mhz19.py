import machine, time

_MHZ19_READ_PPM = b'\xff\x01\x86\x00\x00\x00\x00\x00\x79'
_MHZ19_ZERO_CALIB = b'\xff\x01\x87\x00\x00\x00\x00\x00\x79'
_MHZ19_SPAN_CALIB = b'\xff\x01\x88\x00\x00\x00\x00\x00\x79'
_MHZ19_AUTO_CALIB_ON = b'\xff\x01\x79\xa0\x00\x00\x00\x00\x79'
_MHZ19_AUTO_CALIB_ON = b'\xff\x01\x79\x00\x00\x00\x00\x00\x79'

class MHZ19:
    def __init__(self, uart_id, baudrate=9600, refresh_rate=3000):
        """ A refresh_rate more frequent than 1000ms returns no new data """
        self._uart = machine.UART(uart_id, baudrate=baudrate)
        self._buf = bytearray(9)

        self._last_reading = 0
        self._refresh_rate = max(refresh_rate, 1000)
        self._read()

    def _read(self) -> None:
        if (time.ticks_diff(self._last_reading, time.ticks_ms()) * time.ticks_diff(0, 1) < self._refresh_rate):
            return

        self._uart.write(_MHZ19_READ_PPM)
        time.sleep_ms(2)
        self._uart.readinto(self._buf)
        self._last_reading = time.ticks_ms()

    @property
    def temperature(self) -> float:
        self._read()
        return int(self._buf[4]) - 40.0

    @property
    def co2(self) -> float:
        self._read()
        return int(self._buf[2])*256.0 + int(self._buf[3])
