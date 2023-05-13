import consolas
import epaper2in9b
import framebuf
import machine
import writer

EPAPER_WIDTH = const(296)
EPAPER_HEIGHT = const(128)

COLOR_BLACK = const(0)
COLOR_WHITE = const(1)

class Display():
    def __init__(self, spi, cs_pin, dc_pin, rst_pin, busy_pin):
        # set up gpio pins
        self._cs = machine.Pin(cs_pin, machine.Pin.OUT)
        self._dc = machine.Pin(dc_pin, machine.Pin.OUT)
        self._rst = machine.Pin(rst_pin, machine.Pin.OUT)
        self._busy = machine.Pin(busy_pin, machine.Pin.IN)
        # set up epaper device
        self._buf = bytearray(EPAPER_WIDTH * EPAPER_HEIGHT // 8)
        self._fb = epaper2in9b.TextDisplay(EPAPER_WIDTH, EPAPER_HEIGHT, self._buf)
        self._fb.fill(COLOR_WHITE)
        self._writer = writer.Writer(self._fb, consolas)
        self._writer.set_textpos(self._display, 0, 0)
        self._epaper = epaper2in9b.EPD(spi, self._cs, self._dc, self._rst, self._busy)
        self._epaper.set_rotate(epaper2in9b.ROTATE_270)
        self._epaper.init()

    def _write_labels():
        self._writer.set_textpos(display, 0, 0)
        self._writer.printstring('pressure')
        self._writer.set_textpos(display, 0, 68)
        self._writer.printstring('humidity')
        self._writer.set_textpos(display, 143, 0)
        self._writer.printstring('   temp')
        self._writer.set_textpos(display, 143, 68)
        self._writer.printstring('   co2')
        self._writer.set_textpos(display, 0, 0)

    def _write_pressure(pressure):
        self._epaper.draw_filled_rectangle(buf, 0, 30, 136, 60, COLOR_WHITE)
        self._writer.set_textpos(display, 0, 30)
        self._writer.printstring(f'{pressure: 4}hPa', True)

    def _write_humidity(humidity):
        self._epaper.draw_filled_rectangle(buf, 0, 98, 136, 127, COLOR_WHITE)
        self._writer.set_textpos(display, 0, 98)
        self._writer.printstring(f'{humidity: 3}%', True)

    def _write_temperature(temperature):
        self._epaper.draw_filled_rectangle(buf, 143, 30, 295, 60, COLOR_WHITE)
        self._writer.set_textpos(display, 143, 30)
        temp_f = temperature * 9 / 5 + 32
        self._writer.printstring(f'{temperature: 3}C/{temp_f}F', True)

    def _write_co2(co2):
        self._epaper.draw_filled_rectangle(buf, 143, 98, 295, 127, COLOR_WHITE)
        self._writer.set_textpos(display, 143, 98)
        self._writer.printstring(f'{co2: 4}ppm', True)

    def update():
        self._epaper.display_frame(self._buf, None)
