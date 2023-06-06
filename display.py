import consolas
import epaper2in9b
import framebuf
import machine
import writer

EPAPER_WIDTH = const(296)
EPAPER_HEIGHT = const(128)

COLOR_BLACK = const(0)
COLOR_WHITE = const(1)
COLOR_RED = const(2)

class Display():
    def __init__(self, spi_id, pwr_pin, cs_pin, dc_pin, rst_pin, busy_pin):
        # set up gpio pins
        self._pwr = machine.Pin(pwr_pin, machine.Pin.OUT, machine.Pin.PULL_DOWN)
        self._cs = machine.Pin(cs_pin, machine.Pin.OUT)
        self._dc = machine.Pin(dc_pin, machine.Pin.OUT)
        self._rst = machine.Pin(rst_pin, machine.Pin.OUT)
        self._busy = machine.Pin(busy_pin, machine.Pin.IN)
        # set up black display buffers
        self._buf_black = bytearray(EPAPER_WIDTH * EPAPER_HEIGHT // 8)
        self._fb_black = epaper2in9b.TextDisplay(EPAPER_WIDTH, EPAPER_HEIGHT, self._buf_black)
        self._fb_black.fill(COLOR_WHITE)
        self._writer_black = writer.Writer(self._fb_black, consolas)
        self._writer_black.set_textpos(self._fb_black, 0, 0)
        # set up red display buffers
        self._buf_red = bytearray(EPAPER_WIDTH * EPAPER_HEIGHT // 8)
        self._fb_red = epaper2in9b.TextDisplay(EPAPER_WIDTH, EPAPER_HEIGHT, self._buf_red)
        self._fb_red.fill(COLOR_WHITE)
        self._writer_red = writer.Writer(self._fb_red, consolas)
        self._writer_red.set_textpos(self._fb_red, 0, 0)
        # set up epaper device
        spi = machine.SPI(spi_id, 20_000_000)
        self._epaper = epaper2in9b.EPD(spi, self._pwr, self._cs, self._dc, self._rst, self._busy)
        self._epaper.set_rotate(epaper2in9b.ROTATE_270)
        self._epaper.init()

    def _write_text(self, text, x, y, color):
        if color == COLOR_BLACK:
            self._writer_black.set_textpos(self._fb_black, x, y)
            self._writer_black.printstring(text)
        elif color == COLOR_RED:
            self._writer_red.set_textpos(self._fb_red, x, y)
            self._writer_red.printstring(text)

    def _write_labels(self):
        self._write_text('pressure', 0, 0, COLOR_BLACK)
        self._write_text('humidity', 0, 68, COLOR_BLACK)
        self._write_text('   temp', 143, 0, COLOR_BLACK)
        self._write_text('   gas', 143, 68, COLOR_BLACK)

    def _write_pressure(self, pressure):
        self._write_text(f'{pressure: >5.0f}hPa', 0, 30, COLOR_BLACK)

    def _write_humidity(self, humidity):
        self._write_text(f'{humidity: >5.1f}%', 0, 98, COLOR_BLACK)

    def _write_temperature(self, temperature):
        temp_f = int(temperature * 9 / 5 + 32)
        self._write_text(f'{temperature: >3.0f}C/{temp_f:.0f}F', 143, 30, COLOR_BLACK)

    def _write_gas(self, gas):
        self._write_text(f'{gas: >6.0f}ohm', 143, 98, COLOR_BLACK)

    def _write_iaq(self, iaq):
        if iaq < 200:
            self._write_text(f'{iaq: >6.0f}', 143, 98, COLOR_BLACK)
        else:
            self._write_text(f'{iaq: >6.0f}', 143, 98, COLOR_RED)

    def clear(self):
        self._fb_black.fill(COLOR_WHITE)
        self._fb_red.fill(COLOR_WHITE)
        self.draw_buffer()

    def update_values(self, pressure, humidity, temperature, gas, iaq):
        self._fb_black.fill(COLOR_WHITE)
        self._fb_red.fill(COLOR_WHITE)
        self._write_labels()

        if pressure is not None:
            self._write_pressure(pressure)
        if humidity is not None:
            self._write_humidity(humidity)
        if temperature is not None:
            self._write_temperature(temperature)
        if gas is not None:
            self._write_gas(gas)

    def draw_buffer(self):
        self._epaper.display_frame(self._buf_black, self._buf_red)

    def sleep(self):
        self._epaper.sleep()

    def wake(self):
        self._epaper.init()
