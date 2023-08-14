from micropython import const
from time import sleep_ms
import machine
import framebuf
import ustruct
import display

# Display resolution
EPD_WIDTH  = const(128)
EPD_HEIGHT = const(296)

DRIVER_OUTPUT_CONTROL   = const(0x01)
#GATE_DRIVING_VOLTAGE    = const(0x03)  # set gate driving voltage
#SOURCE_DRIVING_VOLTAGE  = const(0x03)  # set source driving voltage
#INITIAL_CODE_SETTING    = const(0x08)  # program initial code setting
#WRITE_INITIAL_CODE      = const(0x09)  # write initial code register
#READ_INITIAL_CODE       = const(0x0A)  # read initial code register
BOOSTER_SOFT_START      = const(0x0C)  # 3-phase booster soft start
DEEP_SLEEP_MODE         = const(0x10)
DATA_ENTRY_MODE         = const(0x11)  # define data entry sequence
SW_RESET                = const(0x12)
#HV_READY_DETECTION      = const(0x14)  # start hv ready detection
#VCI_DETECTION           = const(0x15)
TEMP_SENSOR_CONTROL     = const(0x18)  # set read internal/external temp
#WRITE_TEMPERATURE       = const(0x1A)  # write temperature register
#READ_TEMPERATURE        = const(0x1B)  # read temperature register
#EXT_TEMP_SENSOR_CMD     = const(0x1C)  # send command to external temp sensor
MASTER_ACTIVATION       = const(0x20)  # display update
DISPLAY_UPDATE_CONTROL1 = const(0x21)  # display update ram options
DISPLAY_UPDATE_CONTROL2 = const(0x22)  # display update sequence options
WRITE_RAM_BLACK         = const(0x24)  # write to black image buffer
WRITE_RAM_RED           = const(0x26)  # write to red image buffer
#READ_RAM                = const(0x27)
#VCOM_SENSE              = const(0x28)  # enter vcom sensing conditions
#VCOM_SENSE_DURATION     = const(0x29)  # stabling time between vcom sense/read
#PROGRAM_VCOM_OTP        = const(0x2A)  # program vcom register into otp
#WRITE_VCOM_CONTROL      = const(0x2B)  # write vcom control register (debug)
#WRITE_VCOM              = const(0x2C)  # write vcom register
#READ_OTP_REGISTER       = const(0x2D)  # read display option register
#READ_USER_ID            = const(0x2E)
#READ_STATUS_BIT         = const(0x2F)
#PROGRAM_WS_OTP          = const(0x30)  # program otp of waveform setting
#LOAD_WS_OTP             = const(0x31)  # load otp of waveform setting
#WRITE_LUT_REGISTER      = const(0x32)  # write lut register
#CRC_CALCULATION         = const(0x34)
#READ_CRC_STATUS         = const(0x35)
#PROGRAM_OTP_SELECTION   = const(0x36)
#WRITE_DISPLAY_OPTION    = const(0x37)  # write display option register
#WRITE_USER_ID           = const(0x38)  # write user id register
#OTP_PROGRAM_MODE        = const(0x39)
BORDER_WAVEFORM         = const(0x3C)  # set panel border waveform
#END_OPTION              = const(0x3F)  # option for lut end
#READ_RAM_OPTION         = const(0x41)
SET_RAMX_ADDRESS        = const(0x44)  # ram-x start/end addresses
SET_RAMY_ADDRESS        = const(0x45)  # ram-y start/end addresses
#AUTO_WRITE_RED_RAM      = const(0x46)  # set auto settings for red ram
#AUTO_WRITE_BW_RAM       = const(0x47)  # set auto settings for black/white ram
SET_RAMX_POS            = const(0x4E)  # ram-x address position
SET_RAMY_POS            = const(0x4F)  # ram-y address position
#NOP                     = const(0x7F)  # can be used to terminate frame mem read/write

BUSY = const(1)  # 0=idle, 1=busy

class EPD:
    def __init__(self, spi_id, pwr_pin, cs_pin, dc_pin, rst_pin, busy_pin):
        self.spi = machine.SPI(spi_id, 20_000_000)
        self.pwr = machine.Pin(pwr_pin, machine.Pin.OUT, machine.Pin.PULL_DOWN)
        self.cs = machine.Pin(cs_pin, machine.Pin.OUT, value=1)
        self.dc = machine.Pin(dc_pin, machine.Pin.OUT, value=0)
        self.rst = machine.Pin(rst_pin, machine.Pin.OUT, value=0)
        self.busy = machine.Pin(busy_pin, machine.Pin.IN)
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT
        self.rotate = display.ROTATE_0

    def _command(self, command, data=None):
        self.dc.off()
        self.cs.off()
        self.spi.write(bytearray([command]))
        if data is not None:
            self._data(data)
        self.cs.on()

    def _data(self, data):
        self.dc.on()
        self.cs.off()
        self.spi.write(data)
        self.cs.on()

    def init(self):
        self.pwr.on()
        sleep_ms(10)
        self._reset()  # hw then sw reset
        self._command(DRIVER_OUTPUT_CONTROL, b'\x27\x01\x01')
        self._command(DATA_ENTRY_MODE, b'\x01')  # decrement y, increment x for ram iteration
        self._command(SET_RAMX_ADDRESS, b'\x00\x0F')  # (0x0f + 1) * 8 = 128
        self._command(SET_RAMY_ADDRESS, b'\x27\x01\x00\x00')  # (0x127 + 1) = 296
        self._command(BORDER_WAVEFORM, b'\x05')
        self._command(TEMP_SENSOR_CONTROL, b'\x80')  # \x80 external temp, \x48 internal temp
        self._command(DISPLAY_UPDATE_CONTROL1, b'\x80\x80')  # normal BW, invert RED, source s8-s167
        self._reset_write_head()
        self.wait_until_idle()

    def wait_until_idle(self):
        retries=0
        while self.busy.value() == BUSY and retries < 200:
            retries += 1
            sleep_ms(100)
        print(f"epaper wait time: {0.1*retries}s")

    def _reset(self):
        self.pwr.on()
        self.rst.on()
        sleep_ms(200)
        self.rst.off()
        sleep_ms(2)
        self.rst.on()
        sleep_ms(200)
        self._command(SW_RESET)
        sleep_ms(50)

    # to wake call init()
    def sleep(self):
        self.wait_until_idle()
        self._command(DEEP_SLEEP_MODE)
        sleep_ms(2000)
        self.pwr.off()

    def _reset_write_head(self):
        self._command(SET_RAMX_POS, b'\x00')
        self._command(SET_RAMY_POS, b'\x27\x01')

    # display VLSB framebuf as VMSB
    def display_frame(self, frame_buffer_black, frame_buffer_red):
        if (frame_buffer_black != None):
            self._reset_write_head()
            self._command(WRITE_RAM_BLACK)
            sleep_ms(2)
            for j in range(EPD_HEIGHT, 0, -1):
                for i in range(0, EPD_WIDTH // 8):
                    idx = (i * EPD_HEIGHT) + (j-1)
                    self._data(bytearray([display._reverse_mask(frame_buffer_black[idx])]))
            sleep_ms(2)
        if (frame_buffer_red != None):
            self._reset_write_head()
            self._command(WRITE_RAM_RED)
            sleep_ms(2)
            for j in range(EPD_HEIGHT, 0, -1):
                for i in range(0, EPD_WIDTH // 8):
                    idx = (i * EPD_HEIGHT) + (j-1)
                    self._data(bytearray([display._reverse_mask(frame_buffer_red[idx])]))
            sleep_ms(2)

        self._command(DISPLAY_UPDATE_CONTROL2, b'\xF7')
        self._command(MASTER_ACTIVATION)
        self.wait_until_idle()

    # FIXME: needs to coordinate with display.TextDisplay, needs redesigning
    def display_frame_universal(self, frame_buffer_black, frame_buffer_red):
        # initialize with values for ROTATE_0
        width_start, width_end, width_step = 0, self.width // 8, 1
        height_start, height_end, height_step = 0, self.height, 1
        reverse = False
        row_length = self.width // 8

        if (self.rotate == display.ROTATE_90):
            width_end = self.width
            height_start, height_end, height_step = (self.height // 8) - 1, -1, -1
            row_length = self.width
        elif (self.rotate == display.ROTATE_180):
            width_start, width_end, width_step = (self.width // 8) - 1, -1, -1
            height_start, height_end, height_step = self.height - 1, -1, -1
            reverse = True  # convert LSB to MSB
        elif (self.rotate == display.ROTATE_270):
            width_start, width_end, width_step = self.width - 1, -1, -1
            height_end = self.height // 8
            row_length = self.width
            reverse = True  # convert LSB to MSB

        if (frame_buffer_black != None):
            self._reset_write_head()
            self._command(WRITE_RAM_BLACK)
            sleep_ms(2)
            for i in range(width_start, width_end, width_step):
                for j in range(height_start, height_end, height_step):
                    idx = (j * row_length) + i
                    b = frame_buffer_black[idx]
                    if (reverse):
                        b = display._reverse_mask(b)
                    self._data(bytearray([b]))
            sleep_ms(2)

        if (frame_buffer_red != None):
            self._reset_write_head()
            self._command(WRITE_RAM_RED)
            sleep_ms(2)
            for i in range(width_start, width_end, width_step):
                for j in range(height_start, height_end, height_step):
                    idx = (j * row_length) + i
                    b = frame_buffer_red[idx]
                    if (reverse):
                        b = display._reverse_mask(b)
                    self._data(bytearray([b]))
            sleep_ms(2)

        self._command(DISPLAY_UPDATE_CONTROL2, b'\xF7')
        self._command(MASTER_ACTIVATION)
        self.wait_until_idle()

    def set_rotate(self, rotate):
        if (rotate == display.ROTATE_0):
            self.rotate = display.ROTATE_0
            self.width = EPD_WIDTH
            self.height = EPD_HEIGHT
        elif (rotate == display.ROTATE_90):
            self.rotate = display.ROTATE_90
            self.width = EPD_HEIGHT
            self.height = EPD_WIDTH
        elif (rotate == display.ROTATE_180):
            self.rotate = display.ROTATE_180
            self.width = EPD_WIDTH
            self.height = EPD_HEIGHT
        elif (rotate == display.ROTATE_270):
            self.rotate = display.ROTATE_270
            self.width = EPD_HEIGHT
            self.height = EPD_WIDTH
