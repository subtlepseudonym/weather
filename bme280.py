import struct
from time import sleep_ms

_BME280_CHIPID = const(0x60)
_BME280_REGISTER_CHIPID = const(0xD0)
OVERSCAN_X1 = const(0x01)  # overscan for temp, humidity
OVERSCAN_X16 = const(0x05)  # overscan for pressure
IIR_FILTER_DISABLE = const(0)

MODE_SLEEP = const(0x00)
MODE_FORCE = const(0x01)
MODE_NORMAL = const(0x03)
_BME280_MODES = (MODE_SLEEP, MODE_FORCE, MODE_NORMAL)

_BME280_REGISTER_SOFTRESET = const(0xE0)
_BME280_REGISTER_CTRL_HUM = const(0xF2)
_BME280_REGISTER_STATUS = const(0xF3)
_BME280_REGISTER_CTRL_MEAS = const(0xF4)
_BME280_REGISTER_CONFIG = const(0xF5)
_BME280_REGISTER_PRESSUREDATA = const(0xF7)
_BME280_REGISTER_TEMPDATA = const(0xFA)
_BME280_REGISTER_HUMIDDATA = const(0xFD)

class BME280:
    def __init__(self, spi, cs):
        self._spi = spi
        self._cs = cs
        # Set some reasonable defaults.
        self._iir_filter = IIR_FILTER_DISABLE
        self.overscan_humidity = OVERSCAN_X1
        self.overscan_temperature = OVERSCAN_X1
        self.overscan_pressure = OVERSCAN_X16
        self._t_standby = 0x02  # 125ms
        self._mode = MODE_SLEEP
        self.reset()
        self._read_coefficients()
        self._write_ctrl_meas()
        self._write_config()
        self._t_fine = None
        self.sea_level_pressure = 1013.25  # pressure in hectoPascals at sea level

        self._cs.off()
        chip_id = self._read_register(_BME280_REGISTER_CHIPID, 1)[0]
        if chip_id != _BME280_CHIPID:
            raise RuntimeError("Failed to find BME280: chip_id 0x%x" % chip_id)
        self._cs.on()

    def _read_register(self, register: int, length: int) -> bytearray:
        register = (register | 0x80) & 0xFF  # bit 7 high
        self._spi.write(bytearray([register]))
        result = bytearray(length)
        self._spi.readinto(result)
        return result

    def _write_register_byte(self, register: int, value: int):
        register &= 0x7F  # bit 7 low
        self._spi.write(bytes([register, value & 0xFF]))

    def _read_coefficients(self) -> None:
        """Read & save the calibration coefficients"""
        self._cs.off()
        coeff = self._read_register(0x88, 24)  # BME280_REGISTER_DIG_T1
        coeff = list(struct.unpack("<HhhHhhhhhhhh", bytes(coeff)))
        coeff = [float(i) for i in coeff]
        self._temp_calib = coeff[:3]
        self._pressure_calib = coeff[3:]

        self._humidity_calib = [0] * 6
        self._humidity_calib[0] = self._read_register(0xA1, 1)[0]  # BME280_REGISTER_DIG_H1
        coeff = self._read_register(0xE1, 7)  # BME280_REGISTER_DIG_H2
        self._cs.on()
        coeff = list(struct.unpack("<hBbBbb", bytes(coeff)))
        self._humidity_calib[1] = float(coeff[0])
        self._humidity_calib[2] = float(coeff[1])
        self._humidity_calib[3] = float((coeff[2] << 4) | (coeff[3] & 0xF))
        self._humidity_calib[4] = float((coeff[4] << 4) | (coeff[3] >> 4))
        self._humidity_calib[5] = float(coeff[5])

    def _write_ctrl_meas(self) -> None:
        """
        Write the values to the ctrl_meas and ctrl_hum registers in the device
        ctrl_meas sets the pressure and temperature data acquisition options
        ctrl_hum sets the humidity oversampling and must be written to first
        """
        self._cs.off()
        self._write_register_byte(_BME280_REGISTER_CTRL_HUM, self.overscan_humidity)
        self._write_register_byte(_BME280_REGISTER_CTRL_MEAS, self._ctrl_meas)
        self._cs.on()

    def _write_config(self) -> None:
        normal_flag = False
        if self._mode == MODE_NORMAL:
            # Writes to the config register might be ignored while in Normal mode
            normal_flag = True
            self.mode = MODE_SLEEP
        self._cs.off()
        self._write_register_byte(_BME280_REGISTER_CONFIG, self._config)
        self._cs.on()
        if normal_flag:
            self.mode = MODE_NORMAL

    def _compensate_pressure(self, raw: float, t_fine: float):
        # Algorithm from the BME280 driver
        # https://github.com/BoschSensortec/BME280_driver/blob/master/bme280.c
        var1 = float(t_fine) / 2.0 - 64000.0
        var2 = var1 * var1 * self._pressure_calib[5] / 32768.0
        var2 = var2 + var1 * self._pressure_calib[4] * 2.0
        var2 = var2 / 4.0 + self._pressure_calib[3] * 65536.0
        var3 = self._pressure_calib[2] * var1 * var1 / 524288.0
        var1 = (var3 + self._pressure_calib[1] * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self._pressure_calib[0]
        if not var1:  # avoid exception caused by division by zero
            print("ERR: Invalid result possibly related to error while reading the calibration registers")
            return 0.0
        pressure = 1048576.0 - raw
        pressure = ((pressure - var2 / 4096.0) * 6250.0) / var1
        var1 = self._pressure_calib[8] * pressure * pressure / 2147483648.0
        var2 = pressure * self._pressure_calib[7] / 32768.0
        pressure = pressure + (var1 + var2 + self._pressure_calib[6]) / 16.0

        pressure /= 100
        return pressure

    def _compensate_temperature(self, raw: float) -> (float, int):
        # https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf 4.2.3
        part_1 = (raw / 16384.0 - self._temp_calib[0] / 1024.0) * self._temp_calib[1]
        part_2 = ((raw / 131072.0 - self._temp_calib[0] / 8192.0) ** 2) * self._temp_calib[2]
        t_fine = int(part_1 + part_2)
        return t_fine / 5120.0, t_fine

    def _compensate_humidity(self, raw: float, t_fine: float):
        var1 = float(t_fine) - 76800.0
        var2 = self._humidity_calib[3] * 64.0 + (self._humidity_calib[4] / 16384.0) * var1
        var3 = raw - var2
        var4 = self._humidity_calib[1] / 65536.0
        var5 = 1.0 + (self._humidity_calib[2] / 67108864.0) * var1
        var6 = 1.0 + (self._humidity_calib[5] / 67108864.0) * var1 * var5
        var6 = var3 * var4 * (var5 * var6)
        humidity = var6 * (1.0 - self._humidity_calib[0] * var6 / 524288.0)

        #if humidity > 100:
        #    return 100
        #if humidity < 0:
        #    return 0
        return humidity


    @property
    def mode(self) -> int:
        return self._mode

    @mode.setter
    def mode(self, value: int) -> None:
        if not value in _BME280_MODES:
            raise ValueError("Mode '%s' not supported" % (value))
        self._mode = value
        self._write_ctrl_meas()

    @property
    def _ctrl_meas(self) -> int:
        ctrl_meas = self.overscan_temperature << 5
        ctrl_meas += self.overscan_pressure << 2
        ctrl_meas += self.mode
        return ctrl_meas

    @property
    def _config(self) -> int:
        """Value to be written to the device's config register"""
        config = 0
        if self.mode == 0x03:  # MODE_NORMAL
            config += self._t_standby << 5
        if self._iir_filter:
            config += self._iir_filter << 2
        return config


    def chip_id(self):
        return self._read(_BME280_REGISTER_CHIPID, 1)[0]

    def reset(self) -> None:
        self._write_register_byte(_BME280_REGISTER_SOFTRESET, 0xB6)
        sleep_ms(4)

    def read(self):
        self._cs.off()
        if self.mode != MODE_NORMAL:
            self.mode = MODE_FORCE
            while self._read_register(_BME280_REGISTER_STATUS, 1)[0] & 0x08:
                sleep_ms(2)

        # burst read from 0xF7 to 0xFE
        raw = self._read_register(_BME280_REGISTER_PRESSUREDATA, 8)
        # read 20-bit float from 0xF7 to 0xF9, then drop lowest four bits
        pressure_raw = (raw[0] << 12) + (raw[1] << 4) + (raw[2] >> 4)
        # read 24-bit float from 0xFA to 0xFC, then drop lowest four bits
        temp_raw = (raw[3] << 12) + (raw[4] << 4) + (raw[5] >> 4)
        humid_raw = (raw[6] << 8) + raw[7]

        temperature, t_fine = self._compensate_temperature(temp_raw)
        pressure = self._compensate_pressure(pressure_raw, t_fine)
        humidity = self._compensate_humidity(humid_raw, t_fine)
        self._cs.on()
        return (pressure, temperature, humidity)

