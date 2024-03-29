import machine
import math
import struct
import time

_BME680_CHIPID = const(0x61)

_BME680_REG_CHIPID = const(0xD0)
_BME680_REG_VARIANT = const(0xF0)
_BME680_BME680_COEFF_ADDR1 = const(0x89)
_BME680_BME680_COEFF_ADDR2 = const(0xE1)
_BME680_BME680_RES_HEAT_0 = const(0x5A)
_BME680_BME680_GAS_WAIT_0 = const(0x64)

_BME680_REG_SOFTRESET = const(0xE0)
_BME680_REG_CTRL_GAS = const(0x71)
_BME680_REG_CTRL_HUM = const(0x72)
_BME680_REG_STATUS = const(0x73)
_BME680_REG_CTRL_MEAS = const(0x74)
_BME680_REG_CONFIG = const(0x75)

_BME680_REG_MEAS_STATUS = const(0x1D)
_BME680_REG_PDATA = const(0x1F)
_BME680_REG_TDATA = const(0x22)
_BME680_REG_HDATA = const(0x25)
_BME680_REG_GDATA = const(0x2A)

_BME680_SAMPLERATES = (0, 1, 2, 4, 8, 16)
_BME680_FILTERSIZES = (0, 1, 3, 7, 15, 31, 63, 127)

_BME680_RUNGAS = const(0x10)

_IAQ_GAS_REFERENCE = const(2500.0)
_IAQ_HUMIDITY_REFERENCE = const(40.0)
#_IAQ_GAS_LOWER_LIMIT = const(10000.0)
#_IAQ_GAS_UPPER_LIMIT = const(300000.0)
_IAQ_GAS_LOWER_LIMIT = const(2000.0)
_IAQ_GAS_UPPER_LIMIT = const(50000.0)

# lookup tables for gas resistance calculation
_LOOKUP_TABLE_1 = (
    2147483647.0,
    2147483647.0,
    2147483647.0,
    2147483647.0,
    2147483647.0,
    2126008810.0,
    2147483647.0,
    2130303777.0,
    2147483647.0,
    2147483647.0,
    2143188679.0,
    2136746228.0,
    2147483647.0,
    2126008810.0,
    2147483647.0,
    2147483647.0,
)

_LOOKUP_TABLE_2 = (
    4096000000.0,
    2048000000.0,
    1024000000.0,
    512000000.0,
    255744255.0,
    127110228.0,
    64000000.0,
    32258064.0,
    16016016.0,
    8000000.0,
    4000000.0,
    2000000.0,
    1000000.0,
    500000.0,
    250000.0,
    125000.0,
)

class BME680:
    def __init__(self, spi_id, cs_pin, refresh_rate: int = 100, t_fine_offset: float = 0, temp_offset: float = 0, humidity_offset: float = 0, debug: bool = False):
        self._spi = machine.SPI(spi_id, 100_000)
        self._cs = machine.Pin(cs_pin, machine.Pin.OUT)

        self._pressure_oversample = 0b011
        self._temp_oversample = 0b100
        self._humidity_oversample = 0b010
        self._filter = 0b011

        self._adc_pres = None
        self._adc_temp = None
        self._adc_hum = None
        self._adc_gas = None
        self._gas_range = None
        self._gas_reference = _IAQ_GAS_REFERENCE
        self._t_fine = None
        self.set_temperature_offset(t_fine_offset)
        self._temp_offset = temp_offset
        self._humidity_offset = humidity_offset

        self._last_reading = 0
        self._min_refresh_time = refresh_rate
        self._debug = debug
        self.sea_level_pressure = 1013.25

        self._write(_BME680_REG_SOFTRESET, [0xB6])
        time.sleep_ms(10)

        # Check device ID.
        chip_id = self._read(_BME680_REG_CHIPID, 1)[0]
        if chip_id != _BME680_CHIPID:
            raise RuntimeError("Failed to find BME680! Chip ID 0x%x" % chip_id)

        # Get variant
        self._chip_variant = self._read(_BME680_REG_VARIANT, 1)[0]

        self._read_calibration()

        # set up gas heater
        self._write(_BME680_BME680_RES_HEAT_0, [0x73])  # 320 degrees C
        self._write(_BME680_BME680_GAS_WAIT_0, [0x65])  # 148ms

    def set_temperature_offset(self, value):
        """Set temperature offset in degrees Celsius.
        Original implementation: https://github.com/pimoroni/bme680-python/pull/13
        Additional discussion:   https://github.com/pimoroni/bme680-python/issues/11
        """
        if value == 0:
            self._t_fine_offset = 0
        else:
            self._t_fine_offset = int(math.copysign((((int(abs(value) * 100)) << 8) - 128) / 5, value))

    @property
    def temperature(self) -> float:
        """The compensated temperature in degrees Celsius."""
        self._perform_reading()
        calc_temp = ((self._t_fine * 5) + 128) / 256
        return (calc_temp / 100) + self._temp_offset

    @property
    def pressure(self) -> float:
        """The barometric pressure in hectoPascals"""
        self._perform_reading()
        var1 = (self._t_fine / 2) - 64000
        var2 = ((var1 / 4) * (var1 / 4)) / 2048
        var2 = (var2 * self._pressure_calibration[5]) / 4
        var2 = var2 + (var1 * self._pressure_calibration[4] * 2)
        var2 = (var2 / 4) + (self._pressure_calibration[3] * 65536)
        var1 = (
            (((var1 / 4) * (var1 / 4)) / 8192)
            * (self._pressure_calibration[2] * 32)
            / 8
        ) + ((self._pressure_calibration[1] * var1) / 2)
        var1 = var1 / 262144
        var1 = ((32768 + var1) * self._pressure_calibration[0]) / 32768
        calc_pres = 1048576 - self._adc_pres
        calc_pres = (calc_pres - (var2 / 4096)) * 3125
        calc_pres = (calc_pres / var1) * 2
        var1 = (
            self._pressure_calibration[8] * (((calc_pres / 8) * (calc_pres / 8)) / 8192)
        ) / 4096
        var2 = ((calc_pres / 4) * self._pressure_calibration[7]) / 8192
        var3 = (((calc_pres / 256) ** 3) * self._pressure_calibration[9]) / 131072
        calc_pres += (var1 + var2 + var3 + (self._pressure_calibration[6] * 128)) / 16
        return calc_pres / 100

    @property
    def humidity(self) -> float:
        """The relative humidity in RH %"""
        self._perform_reading()
        temp_scaled = ((self._t_fine * 5) + 128) / 256
        var1 = (self._adc_hum - (self._humidity_calibration[0] * 16)) - (
            (temp_scaled * self._humidity_calibration[2]) / 200
        )
        var2 = (
            self._humidity_calibration[1]
            * (
                ((temp_scaled * self._humidity_calibration[3]) / 100)
                + (
                    (
                        (
                            temp_scaled
                            * ((temp_scaled * self._humidity_calibration[4]) / 100)
                        )
                        / 64
                    )
                    / 100
                )
                + 16384
            )
        ) / 1024
        var3 = var1 * var2
        var4 = self._humidity_calibration[5] * 128
        var4 = (var4 + ((temp_scaled * self._humidity_calibration[6]) / 100)) / 16
        var5 = ((var3 / 16384) * (var3 / 16384)) / 1024
        var6 = (var4 * var5) / 2
        calc_hum = (((var3 + var6) / 1024) * 1000) / 4096
        calc_hum /= 1000  # get back to RH

        calc_hum = min(calc_hum, 100)
        calc_hum = max(calc_hum, 0)
        return calc_hum + self._humidity_offset

    @property
    def gas_resistance(self) -> int:
        """The gas resistance in ohms"""
        self._perform_reading()
        if self._chip_variant == 0x01:
            # taken from https://github.com/BoschSensortec/BME68x-Sensor-API
            var1 = 262144 >> self._gas_range
            var2 = self._adc_gas - 512
            var2 *= 3
            var2 = 4096 + var2
            calc_gas_res = (1000 * var1) / var2
            calc_gas_res = calc_gas_res * 100
        else:
            var1 = (
                (1340 + (5 * self._sw_err)) * (_LOOKUP_TABLE_1[self._gas_range])
            ) / 65536
            var2 = ((self._adc_gas * 32768) - 16777216) + var1
            var3 = (_LOOKUP_TABLE_2[self._gas_range] * var1) / 512
            calc_gas_res = (var3 + (var2 / 2)) / var2
        return int(calc_gas_res)

    def burn_in(self, count=10) -> None:
        for i in range(count):
            time.sleep_ms(self._min_refresh_time+2)
            self._perform_reading()

    @property
    def indoor_air_quality(self) -> float:
        readings = 5
        for i in range(readings):
            self._gas_reference += self.gas_resistance
            time.sleep_ms(self._min_refresh_time+2)
        self._gas_reference /= readings
        gas_score = ((0.75 / (_IAQ_GAS_UPPER_LIMIT - _IAQ_GAS_LOWER_LIMIT) * self._gas_reference) - (_IAQ_GAS_LOWER_LIMIT * (0.75 / (_IAQ_GAS_UPPER_LIMIT - _IAQ_GAS_LOWER_LIMIT)))) * 100.0
        if gas_score > 75:
            gas_score = 75
        elif gas_score < 0:
            gas_score = 0

        humidity_score = 25.0
        humidity = self.humidity
        if humidity < 38:
            humidity_score = 0.25 / _IAQ_HUMIDITY_REFERENCE * humidity * 100.0
        elif humidity > 42:
            humidity_score = ((-0.25 / (100 - _IAQ_HUMIDITY_REFERENCE) * humidity) + 0.416666) * 100.0

        return (100.0 - gas_score - humidity_score) * 5.0

    def _perform_reading(self) -> None:
        """Perform a single-shot reading from the sensor and fill internal data structure for
        calculations"""
        if (time.ticks_diff(self._last_reading, time.ticks_ms()) * time.ticks_diff(0, 1) < self._min_refresh_time):
            return

        time.sleep_ms(2)
        # set filter
        self._write(_BME680_REG_CONFIG, [self._filter << 2])
        # turn on humidity oversample
        self._write(_BME680_REG_CTRL_HUM, [self._humidity_oversample])
        # turn on temp oversample & pressure oversample
        self._write(
            _BME680_REG_CTRL_MEAS,
            [(self._temp_oversample << 5) | (self._pressure_oversample << 2)],
        )
        # gas measurements enabled
        if self._chip_variant == 0x01:
            self._write(_BME680_REG_CTRL_GAS, [_BME680_RUNGAS << 1])
        else:
            self._write(_BME680_REG_CTRL_GAS, [_BME680_RUNGAS])
        ctrl = self._read(_BME680_REG_CTRL_MEAS, 1)[0]
        ctrl = (ctrl & 0xFC) | 0x01  # enable single shot!
        self._write(_BME680_REG_CTRL_MEAS, [ctrl])
        new_data = False
        while not new_data:
            data = self._read(_BME680_REG_MEAS_STATUS, 17)
            new_data = data[0] & 0x80 != 0
            time.sleep_ms(5)
        self._last_reading = time.ticks_ms()

        self._adc_pres = (data[2] << 12) + (data[3] << 4) + (data[4] >> 4)
        self._adc_temp = (data[5] << 12) + (data[6] << 4) + (data[7] >> 4)

        self._adc_hum = struct.unpack(">H", bytes(data[8:10]))[0]
        if self._chip_variant == 0x01:
            self._adc_gas = int(struct.unpack(">H", bytes(data[15:17]))[0] / 64)
            self._gas_range = data[16] & 0x0F
        else:
            self._adc_gas = int(struct.unpack(">H", bytes(data[13:15]))[0] / 64)
            self._gas_range = data[14] & 0x0F

        var1 = (self._adc_temp / 8) - (self._temp_calibration[0] * 2)
        var2 = (var1 * self._temp_calibration[1]) / 2048
        var3 = ((var1 / 2) * (var1 / 2)) / 4096
        var3 = (var3 * self._temp_calibration[2] * 16) / 16384
        self._t_fine = int(var2 + var3) + self._t_fine_offset

    def _read_calibration(self) -> None:
        """Read & save the calibration coefficients"""
        coeff = self._read(_BME680_BME680_COEFF_ADDR1, 25)
        coeff += self._read(_BME680_BME680_COEFF_ADDR2, 16)

        coeff = list(struct.unpack("<hbBHhbBhhbbHhhBBBHbbbBbHhbb", bytes(coeff[1:39])))
        coeff = [float(i) for i in coeff]
        self._temp_calibration = [coeff[x] for x in [23, 0, 1]]
        self._pressure_calibration = [
            coeff[x] for x in [3, 4, 5, 7, 8, 10, 9, 12, 13, 14]
        ]
        self._humidity_calibration = [coeff[x] for x in [17, 16, 18, 19, 20, 21, 22]]
        self._gas_calibration = [coeff[x] for x in [25, 24, 26]]

        # flip around H1 & H2
        self._humidity_calibration[1] *= 16
        self._humidity_calibration[1] += self._humidity_calibration[0] % 16
        self._humidity_calibration[0] /= 16

        self._heat_range = (self._read(0x02, 1)[0] & 0x30) / 16
        self._heat_val = self._read(0x00, 1)[0]
        self._sw_err = (self._read(0x04, 1)[0] & 0xF0) / 16

    def _read(self, register: int, length: int) -> bytearray:
        if register != _BME680_REG_STATUS:
            # _BME680_REG_STATUS exists in both SPI memory pages
            # For all other registers, we must set the correct memory page
            self._set_spi_mem_page(register)

        register = (register | 0x80) & 0xFF  # Read, bit 7 high
        self._cs(0)
        self._spi.write(bytearray([register]))
        result = bytearray(length)
        self._spi.readinto(result)
        self._cs(1)
        if self._debug:
            print("\t$%02X => %s" % (register, [hex(i) for i in result]))
        return result

    def _write(self, register: int, values) -> None:
        if register != _BME680_REG_STATUS:
            # _BME680_REG_STATUS exists in both SPI memory pages
            # For all other registers, we must set the correct memory page
            self._set_spi_mem_page(register)

        register &= 0x7F  # Write, bit 7 low
        buffer = bytearray(2 * len(values))
        for i, value in enumerate(values):
            buffer[2 * i] = register + i
            buffer[2 * i + 1] = value & 0xFF
        self._cs(0)
        self._spi.write(buffer)
        self._cs(1)
        if self._debug:
            print("\t$%02X <= %s" % (buffer[0], [hex(i) for i in buffer[1:]]))

    def _set_spi_mem_page(self, register: int) -> None:
        spi_mem_page = 0x00
        if register < 0x80:
            spi_mem_page = 0x10
        self._cs(0)
        self._write(_BME680_REG_STATUS, [spi_mem_page])
        self._cs(1)

