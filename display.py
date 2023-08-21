import consolas
import framebuf
import machine
import writer

# Width set assuming 270 degree rotation
EPAPER_WIDTH = const(296)
EPAPER_HEIGHT = const(128)

COLOR_BLACK = const(0)
COLOR_WHITE = const(1)
COLOR_RED = const(2)

# Display orientation
ROTATE_0   = const(0)
ROTATE_90  = const(1)
ROTATE_180 = const(2)
ROTATE_270 = const(3)

# Reverse bit order in byte
def _reverse_mask(b):
    return (((b & 0x1)  << 7) | ((b & 0x2)  << 5) |
            ((b & 0x4)  << 3) | ((b & 0x8)  << 1) |
            ((b & 0x10) >> 1) | ((b & 0x20) >> 3) |
            ((b & 0x40) >> 5) | ((b & 0x80) >> 7))


class TextDisplay(framebuf.FrameBuffer):
    def __init__(self, width, height, buffer):
        self.width = width
        self.height = height
        self.buffer = buffer
        self.mode = framebuf.MONO_VLSB
        super().__init__(self.buffer, self.width, self.height, self.mode)


class Display():
    def __init__(self, epd):
        # set up black display buffers
        self._buf_black = bytearray(EPAPER_WIDTH * EPAPER_HEIGHT // 8)
        self._fb_black = TextDisplay(EPAPER_WIDTH, EPAPER_HEIGHT, self._buf_black)
        self._fb_black.fill(COLOR_WHITE)
        self._writer_black = writer.Writer(self._fb_black, consolas)
        self._writer_black.set_textpos(self._fb_black, 0, 0)
        # set up red display buffers
        self._buf_red = bytearray(EPAPER_WIDTH * EPAPER_HEIGHT // 8)
        self._fb_red = TextDisplay(EPAPER_WIDTH, EPAPER_HEIGHT, self._buf_red)
        self._fb_red.fill(COLOR_WHITE)
        self._writer_red = writer.Writer(self._fb_red, consolas)
        self._writer_red.set_textpos(self._fb_red, 0, 0)
        # set up epaper device
        self._epd = epd
        self._epd.set_rotate(ROTATE_270)
        self._epd.init()

    def _write_text(self, text, x, y, color):
        if color == COLOR_BLACK:
            self._writer_black.set_textpos(self._fb_black, x, y)
            self._writer_black.printstring(text)
        elif color == COLOR_RED:
            self._writer_red.set_textpos(self._fb_red, x, y)
            self._writer_red.printstring(text)

    def _write_labels(self):
        self._write_text(' Air Quality', 0, 0, COLOR_BLACK)
        self._write_text('  CO2', 188, 0, COLOR_BLACK)
        self._write_text(' Temperature', 0, 42, COLOR_BLACK)
        self._write_text('Humidity', 188, 42, COLOR_BLACK)
        self._write_text('Gas Resistance', 0, 84, COLOR_BLACK)
        self._write_text('Pressure', 188, 84, COLOR_BLACK)

    def _write_iaq(self, iaq):
        color = COLOR_BLACK
        if iaq > 150:
            color = COLOR_RED
        self._write_text(f'{iaq: >8.0f}', 0, 21, color)

    def _write_co2(self, co2):
        color = COLOR_BLACK
        if co2 > 900:
            color = COLOR_RED
        self._write_text(f'{co2: >4.0f}ppm', 188, 21, color)

    def _write_temperature(self, temperature):
        color = COLOR_BLACK
        if temperature > 30:
            color = COLOR_RED
        temp_f = int(temperature * 9 / 5 + 32)
        self._write_text(f'{temperature: >5.0f}C {temp_f:.0f}F', 0, 63, color)
        self._write_text(f'/', 72, 63, COLOR_BLACK)  # always draw slash with black

    def _write_humidity(self, humidity):
        color = COLOR_BLACK
        if humidity > 85:
            color = COLOR_RED
        self._write_text(f'{humidity: >5.1f}%', 188, 63, color)

    def _write_gas(self, gas):
        self._write_text(f'{gas: >8.0f}ohm', 0, 105, COLOR_BLACK)

    def _write_pressure(self, pressure):
        self._write_text(f'{pressure: >5.0f}hPa', 188, 105, COLOR_BLACK)

    def clear(self, draw=True):
        self._fb_black.fill(COLOR_WHITE)
        self._fb_red.fill(COLOR_WHITE)
        if draw:
            self.draw_buffer()

    def _update_values(
            self,
            iaq=None,
            co2=None,
            temperature=None,
            humidity=None,
            gas=None,
            pressure=None
    ):
        self._fb_black.fill(COLOR_WHITE)
        self._fb_red.fill(COLOR_WHITE)
        self._write_labels()

        if iaq is not None:
            self._write_iaq(iaq)
        if co2 is not None:
            self._write_co2(co2)
        if temperature is not None:
            self._write_temperature(temperature)
        if humidity is not None:
            self._write_humidity(humidity)
        if gas is not None:
            self._write_gas(gas)
        if pressure is not None:
            self._write_pressure(pressure)

    def update(self, m):
        self._update_values(
            iaq=m.indoor_air_quality,
            co2=m.co2,
            temperature=m.temperature,
            humidity=m.humidity,
            gas=m.gas_resistance,
            pressure=m.pressure,
        )
        self.wake()
        self.draw_buffer()
        self.sleep()

    def draw_buffer(self):
        self._epd.display_frame(self._buf_black, self._buf_red)

    def sleep(self):
        self._epd.sleep()

    def wake(self):
        self._epd.init()
