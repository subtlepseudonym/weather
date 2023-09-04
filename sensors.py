import _thread

class Sensors():
    def __init__(self, dht=None, bme=None, mhz=None, c8d=None, epd=None):
        self.dht = dht
        self.bme = bme
        self.mhz = mhz
        self.c8d = c8d
        self.epd = epd

        self.dht_temperature = 0
        self.bme_temperature = 0
        self.mhz_temperature = 0
        self.epd_temperature = 0
        self._temperature_list = []
        self.temperature = 0  # mean sensor temp

        self.dht_humidity = 0
        self.bme_humidity = 0
        self._humidity_list = []
        self.humidity = 0  # mean sensor humidity

        self.pressure = 0
        self.gas_resistance = 0
        self.indoor_air_quality = 0

        self.mhz_co2 = 0
        self.c8d_co2 = 0
        self._co2_list = []
        self.co2 = 0

    def update(self):
        if self.dht != None:
            self.dht.measure()
            self.dht_temperature = self.dht.temperature()
            self.dht_humidity = self.dht.humidity()

            self._temperature_list.append(self.dht_temperature)
            self._humidity_list.append(self.dht_humidity)

        if self.bme != None:
            self.bme_temperature = self.bme.temperature
            self.bme_humidity = self.bme.humidity
            self.pressure = self.bme.pressure
            self.indoor_air_quality = self.bme.indoor_air_quality
            # take gas res after IAQ because IAQ runs the gas heater several times
            self.gas_resistance = self.bme.gas_resistance

            self._temperature_list.append(self.bme_temperature)
            self._humidity_list.append(self.bme_humidity)

        if self.mhz != None:
            self.mhz_temperature = self.mhz.temperature
            self.mhz_co2 = self.mhz.co2

            self._temperature_list.append(self.mhz_temperature)
            self._co2_list.append(self.mhz_co2)

        if self.c8d != None:
            self.c8d_co2 = self.c8d.co2
            self._co2_list.append(self.c8d_co2)

        if self.epd != None:
            self.epd_temperature = self.epd.temperature
            self._temperature_list.append(self.epd_temperature)

        self.temperature = sum(self._temperature_list) / max(len(self._temperature_list), 1)
        self._temperature_list = []

        self.humidity = sum(self._humidity_list) / max(len(self._humidity_list), 1)
        self._humidity_list = []

        self.co2 = sum(self._co2_list) / max(len(self._co2_list), 1)
        self._co2_list = []

    def print(self):
        print('--------')
        print(f'dht temp:  {self.dht_temperature:6.2f} °C')
        print(f'bme temp:  {self.bme_temperature:6.2f} °C')
        print(f'mhz temp:  {self.mhz_temperature:6.2f} °C')
        print(f'epd temp:  {self.epd_temperature:6.2f} °C')
        print(f'dht humid: {self.dht_humidity:6.1f} %rh')
        print(f'bme humid: {self.bme_humidity:6.1f} %rh')
        print(f'pressure:  {self.pressure:7.2f} hpa')
        print(f'gas res:   {self.gas_resistance:6.0f} ohm')
        print(f'iaq score: {self.indoor_air_quality:6.0f}')
        print(f'mhz co2:   {self.mhz_co2:6.0f} ppm')
        print(f'c8d co2:   {self.c8d_co2:6.0f} ppm')
        print('--------')
