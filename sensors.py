import _thread

class Sensors():
    def __init__(self, dht, bme):
        self.dht = dht
        self.bme = bme

        self.dht_temperature = None
        self.bme_temperature = None
        self.temperature = None  # mean sensor temp
        self.dht_humidity = None
        self.bme_humidity = None
        self.humidity = None  # mean sensor humidity
        self.pressure = None
        self.gas_resistance = None
        self.indoor_air_quality = None

    def update(self):
        self.dht.measure()

        self.dht_temperature = self.dht.temperature()
        self.bme_temperature = self.bme.temperature
        self.temperature = (self.dht_temperature + self.bme_temperature) / 2.0

        self.dht_humidity = self.dht.humidity()
        self.bme_humidity = self.bme.humidity
        self.humidity = (self.dht_humidity + self.bme_humidity) / 2.0

        self.pressure = self.bme.pressure
        self.indoor_air_quality = self.bme.indoor_air_quality
        # take gas res after IAQ because IAQ runs the gas heater several times
        self.gas_resistance = self.bme.gas_resistance

    def print(self):
        print('--------')
        print(f'dht temp:  {self.dht_temperature:6.1f} °C')
        print(f'bme temp:  {self.bme_temperature:6.1f} °C')
        print(f'dht humid: {self.dht_humidity:6.1f} %rh')
        print(f'bme humid: {self.bme_humidity:6.1f} %rh')
        print(f'pressure:  {self.pressure:6.0f} hpa')
        print(f'gas res:   {self.gas_resistance:6.0f} ohm')
        print(f'iaq score: {self.indoor_air_quality:6.0f}')
        print('--------')
