from micropython import const
from time import sleep_ms
import framebuf
import ustruct

# Display resolution
EPD_WIDTH  = const(128)
EPD_HEIGHT = const(296)

# Display commands
PANEL_SETTING                  = const(0x00)
POWER_SETTING                  = const(0x01)
POWER_OFF                      = const(0x02)
#POWER_OFF_SEQUENCE_SETTING     = const(0x03)
POWER_ON                       = const(0x04)
#POWER_ON_MEASURE               = const(0x05)
BOOSTER_SOFT_START             = const(0x06)
#DEEP_SLEEP                     = const(0x07)
DATA_START_TRANSMISSION_1      = const(0x10)
#DATA_STOP                      = const(0x11)
DISPLAY_REFRESH                = const(0x12)
DATA_START_TRANSMISSION_2      = const(0x13)
#PLL_CONTROL                    = const(0x30)
#TEMPERATURE_SENSOR_COMMAND     = const(0x40)
#TEMPERATURE_SENSOR_CALIBRATION = const(0x41)
#TEMPERATURE_SENSOR_WRITE       = const(0x42)
#TEMPERATURE_SENSOR_READ        = const(0x43)
VCOM_AND_DATA_INTERVAL_SETTING = const(0x50)
#LOW_POWER_DETECTION            = const(0x51)
#TCON_SETTING                   = const(0x60)
TCON_RESOLUTION                = const(0x61)
#GET_STATUS                     = const(0x71)
#AUTO_MEASURE_VCOM              = const(0x80)
#VCOM_VALUE                     = const(0x81)
VCM_DC_SETTING_REGISTER        = const(0x82)
#PARTIAL_WINDOW                 = const(0x90)
#PARTIAL_IN                     = const(0x91)
#PARTIAL_OUT                    = const(0x92)
#PROGRAM_MODE                   = const(0xA0)
#ACTIVE_PROGRAM                 = const(0xA1)
#READ_OTP_DATA                  = const(0xA2)
#POWER_SAVING                   = const(0xE3)

# Display orientation
ROTATE_0   = const(0)
ROTATE_90  = const(1)
ROTATE_180 = const(2)
ROTATE_270 = const(3)

BUSY = const(0)  # 0=busy, 1=idle

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


class EPD:
    def __init__(self, spi, pwr, cs, dc, rst, busy):
        self.spi = spi
        self.pwr = pwr
        self.cs = cs
        self.dc = dc
        self.rst = rst
        self.busy = busy
        self.cs.init(self.cs.OUT, value=1)
        self.dc.init(self.dc.OUT, value=0)
        self.rst.init(self.rst.OUT, value=0)
        self.busy.init(self.busy.IN)
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT
        self.rotate = ROTATE_0

    def _command(self, command, data=None):
        self.dc.off()
        self.cs.off()
        self.spi.write(bytearray([command]))
        self.cs.on()
        if data is not None:
            self._data(data)

    def _data(self, data):
        self.dc.on()
        self.cs.off()
        self.spi.write(data)
        self.cs.on()

    def init(self):
        self.pwr.on()
        self.reset()
        self._command(BOOSTER_SOFT_START, b'\x17\x17\x17')
        self._command(POWER_ON)
        self.wait_until_idle()
        self._command(PANEL_SETTING, b'\x8F')
        self._command(VCOM_AND_DATA_INTERVAL_SETTING, b'\x77')
        self._command(TCON_RESOLUTION, ustruct.pack(">BH", EPD_WIDTH, EPD_HEIGHT))
        self._command(VCM_DC_SETTING_REGISTER, b'\x0A')

    def wait_until_idle(self):
        retries=0
        while self.busy.value() == BUSY and retries < 200:
            retries += 1
            sleep_ms(100)
        print(f"epaper wait time: {0.1*retries}s")

    def reset(self):
        self.pwr.on()
        self.rst.on()
        sleep_ms(200)
        self.rst.off()
        sleep_ms(2)
        self.rst.on()
        sleep_ms(200)

    # to wake call reset() or init()
    def sleep(self):
        self._command(VCOM_AND_DATA_INTERVAL_SETTING, b'\x37')
        self._command(VCM_DC_SETTING_REGISTER, b'\x00') # to solve Vcom drop
        self._command(POWER_SETTING, b'\x02\x00\x00\x00') # gate switch to external
        self.wait_until_idle()
        self._command(POWER_OFF)
        sleep_ms(2000)
        self.pwr.off()

    def display_frame(self, frame_buffer_black, frame_buffer_red):
        if (frame_buffer_black != None):
            self._command(DATA_START_TRANSMISSION_1)
            sleep_ms(2)
            for j in range(EPD_HEIGHT, 0, -1):
                for i in range(0, EPD_WIDTH // 8):
                    idx = (i * EPD_HEIGHT) + (j-1)
                    self._data(bytearray([_reverse_mask(frame_buffer_black[idx])]))
            sleep_ms(2)
        if (frame_buffer_red != None):
            self._command(DATA_START_TRANSMISSION_2)
            sleep_ms(2)
            for j in range(EPD_HEIGHT, 0, -1):
                for i in range(0, EPD_WIDTH // 8):
                    idx = (i * EPD_HEIGHT) + (j-1)
                    self._data(bytearray([_reverse_mask(frame_buffer_red[idx])]))
            sleep_ms(2)

        self._command(DISPLAY_REFRESH)
        self.wait_until_idle()

    def display_frame_hlsb(self, frame_buffer_black, frame_buffer_red):
        if (frame_buffer_black != None):
            self._command(DATA_START_TRANSMISSION_1)
            sleep_ms(2)
            for i in range(0, self.width * self.height // 8):
                self._data(bytearray([frame_buffer_black[i]]))
            sleep_ms(2)
        if (frame_buffer_red != None):
            self._command(DATA_START_TRANSMISSION_2)
            sleep_ms(2)
            for i in range(0, self.width * self.height // 8):
                self._data(bytearray([frame_buffer_red[i]]))
            sleep_ms(2)

        self._command(DISPLAY_REFRESH)
        self.wait_until_idle()

    def set_rotate(self, rotate):
        if (rotate == ROTATE_0):
            self.rotate = ROTATE_0
            self.width = EPD_WIDTH
            self.height = EPD_HEIGHT
        elif (rotate == ROTATE_90):
            self.rotate = ROTATE_90
            self.width = EPD_HEIGHT
            self.height = EPD_WIDTH
        elif (rotate == ROTATE_180):
            self.rotate = ROTATE_180
            self.width = EPD_WIDTH
            self.height = EPD_HEIGHT
        elif (rotate == ROTATE_270):
            self.rotate = ROTATE_270
            self.width = EPD_HEIGHT
            self.height = EPD_WIDTH

    def set_pixel(self, frame_buffer, x, y, color):
        if (x < 0 or x >= self.width or y < 0 or y >= self.height):
            return
        if (self.rotate == ROTATE_0):
            self.set_absolute_pixel(frame_buffer, x, y, color)
        elif (self.rotate == ROTATE_90):
            point_temp = x
            x = EPD_WIDTH - y
            y = point_temp
            self.set_absolute_pixel(frame_buffer, x, y, color)
        elif (self.rotate == ROTATE_180):
            x = EPD_WIDTH - x
            y = EPD_HEIGHT- y
            self.set_absolute_pixel(frame_buffer, x, y, color)
        elif (self.rotate == ROTATE_270):
            point_temp = x
            x = y
            y = EPD_HEIGHT - point_temp
            self.set_absolute_pixel(frame_buffer, x, y, color)

    def set_absolute_pixel(self, frame_buffer, x, y, color):
        # NOTE: assumes the use of MONO_VLSB frame buffer
        # To avoid display orientation effects
        # use EPD_WIDTH instead of self.width
        # use EPD_HEIGHT instead of self.height
        if (x < 0 or x >= EPD_WIDTH or y < 0 or y >= EPD_HEIGHT):
            return
        if (color):
            frame_buffer[(x // 8 * EPD_HEIGHT) + ((EPD_HEIGHT - 1) - y)] |= 0x80 >> (7 - (x % 8))
        else:
            frame_buffer[(x // 8 * EPD_HEIGHT) + ((EPD_HEIGHT - 1) - y)] &= ~(0x80 >> (x % 8))

    def draw_line(self, frame_buffer, x0, y0, x1, y1, color):
        # Bresenham algorithm
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while((x0 != x1) and (y0 != y1)):
            self.set_pixel(frame_buffer, x0, y0 , color)
            if (2 * err >= dy):
                err += dy
                x0 += sx
            if (2 * err <= dx):
                err += dx
                y0 += sy

    def draw_horizontal_line(self, frame_buffer, x, y, width, color):
        for i in range(x, x + width):
            self.set_pixel(frame_buffer, i, y, color)

    def draw_vertical_line(self, frame_buffer, x, y, height, color):
        for i in range(y, y + height):
            self.set_pixel(frame_buffer, x, i, color)

    def draw_rectangle(self, frame_buffer, x0, y0, x1, y1, color):
        min_x = x0 if x1 > x0 else x1
        max_x = x1 if x1 > x0 else x0
        min_y = y0 if y1 > y0 else y1
        max_y = y1 if y1 > y0 else y0
        self.draw_horizontal_line(frame_buffer, min_x, min_y, max_x - min_x + 1, color)
        self.draw_horizontal_line(frame_buffer, min_x, max_y, max_x - min_x + 1, color)
        self.draw_vertical_line(frame_buffer, min_x, min_y, max_y - min_y + 1, color)
        self.draw_vertical_line(frame_buffer, max_x, min_y, max_y - min_y + 1, color)

    def draw_filled_rectangle(self, frame_buffer, x0, y0, x1, y1, color):
        min_x = x0 if x1 > x0 else x1
        max_x = x1 if x1 > x0 else x0
        min_y = y0 if y1 > y0 else y1
        max_y = y1 if y1 > y0 else y0
        for i in range(min_x, max_x + 1):
            self.draw_vertical_line(frame_buffer, i, min_y, max_y - min_y + 1, color)

    def draw_circle(self, frame_buffer, x, y, radius, color):
        # Bresenham algorithm
        x_pos = -radius
        y_pos = 0
        err = 2 - 2 * radius
        if (x >= self.width or y >= self.height):
            return
        while True:
            self.set_pixel(frame_buffer, x - x_pos, y + y_pos, color)
            self.set_pixel(frame_buffer, x + x_pos, y + y_pos, color)
            self.set_pixel(frame_buffer, x + x_pos, y - y_pos, color)
            self.set_pixel(frame_buffer, x - x_pos, y - y_pos, color)
            e2 = err
            if (e2 <= y_pos):
                y_pos += 1
                err += y_pos * 2 + 1
                if(-x_pos == y_pos and e2 <= x_pos):
                    e2 = 0
            if (e2 > x_pos):
                x_pos += 1
                err += x_pos * 2 + 1
            if x_pos > 0:
                break

    def draw_filled_circle(self, frame_buffer, x, y, radius, color):
        # Bresenham algorithm
        x_pos = -radius
        y_pos = 0
        err = 2 - 2 * radius
        if (x >= self.width or y >= self.height):
            return
        while True:
            self.set_pixel(frame_buffer, x - x_pos, y + y_pos, color)
            self.set_pixel(frame_buffer, x + x_pos, y + y_pos, color)
            self.set_pixel(frame_buffer, x + x_pos, y - y_pos, color)
            self.set_pixel(frame_buffer, x - x_pos, y - y_pos, color)
            self.draw_horizontal_line(frame_buffer, x + x_pos, y + y_pos, 2 * (-x_pos) + 1, color)
            self.draw_horizontal_line(frame_buffer, x + x_pos, y - y_pos, 2 * (-x_pos) + 1, color)
            e2 = err
            if (e2 <= y_pos):
                y_pos += 1
                err += y_pos * 2 + 1
                if(-x_pos == y_pos and e2 <= x_pos):
                    e2 = 0
            if (e2 > x_pos):
                x_pos  += 1
                err += x_pos * 2 + 1
            if x_pos > 0:
                break
