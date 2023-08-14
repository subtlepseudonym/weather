import consolas
import wvsepd29b
import framebuf
from machine import Pin, SPI
from writer import Writer

spi = SPI(1, 20_000_000)
cs = Pin(15, Pin.OUT)
dc = Pin(2, Pin.OUT)
rst = Pin(4, Pin.OUT)
busy = Pin(12, Pin.IN)

width = 296
height = 128
black = 0
white = 1
red = 1

e = wvsepd29b.EPD(spi, cs, dc, rst, busy)
buf = bytearray(width * height // 8)

e.set_rotate(wvsepd29b.ROTATE_270)
#fb = framebuf.FrameBuffer(buf, height, width, framebuf.MONO_HLSB)  # portrait
#fb = framebuf.FrameBuffer(buf, width, height, framebuf.MONO_VLSB)  # landscape
display = wvsepd29b.TextDisplay(296, 128, buf)
w = Writer(display, consolas)
Writer.set_textpos(display, 0, 0)

def clear():
    display.fill(white)
    e.display_frame_hlsb(buf, buf)

def _write_labels():
    w.set_textpos(display, 0, 0)
    w.printstring('pressure', True)
    w.set_textpos(display, 0, 68)
    w.printstring('humidity', True)
    w.set_textpos(display, 142, 0)
    w.printstring('   temp', True)
    w.set_textpos(display, 142, 68)
    w.printstring('   co2', True)
    w.set_textpos(display, 0, 0)

def _write_pressure(pressure):
    e.draw_filled_rectangle(buf, 0, 30, 136, 60, False)
    w.set_textpos(display, 0, 30)
    w.printstring(f'{pressure: 4}hPa', True)

def _write_humidity(humidity):
    e.draw_filled_rectangle(buf, 0, 98, 136, 127, False)
    w.set_textpos(display, 0, 98)
    w.printstring(f'{humidity: 3}%', True)

def _write_temperature(temperature):
    e.draw_filled_rectangle(buf, 142, 30, 295, 60, False)
    w.set_textpos(display, 142, 30)
    temp_f = temperature * 9 / 5 + 32
    w.printstring(f'{temperature: 3}C/{temp_f}F', True)

def _write_co2(co2):
    e.draw_filled_rectangle(buf, 142, 98, 295, 127, False)
    w.set_textpos(display, 142, 98)
    w.printstring(f'{co2: 4}ppm', True)

def display_test():
    display.fill(white)
    _write_labels()
    _write_pressure(1015)
    _write_humidity(100)
    _write_temperature(100)
    _write_co2(1000)
    e.display_frame(buf, None)

display.fill(white)
e.init()
