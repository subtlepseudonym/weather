import machine, network, _thread
import prometheus_express as prometheus

class Prometheus():
    def __init__(self):
        self.registry = prometheus.CollectorRegistry(namespace='weather')
        self.temperature_gauge = prometheus.Gauge(
            name='temperature_celsius',
            desc='temperature sensor output',
            labels=['sensor'],
            registry=self.registry,
        )
        self.humidity_gauge = prometheus.Gauge(
            name='humidity_ratio',
            desc='humidity sensor output',
            labels=['sensor'],
            registry=self.registry,
        )
        self.pressure_gauge = prometheus.Gauge(
            name='pressure_hectopascals',
            desc='atmospheric pressure sensor output',
            labels=['sensor'],
            registry=self.registry,
        )
        self.gas_resistance_gauge = prometheus.Gauge(
            name='gas_resistance_ohms',
            desc='metal-oxide gas sensor resistance value',
            labels=['sensor'],
            registry=self.registry,
        )
        self.indoor_air_quality_gauge = prometheus.Gauge(
            name='indoor_air_quality_score',
            desc='score for indoor air quality ranging from 0-500',
            labels=['sensor'],
            registry=self.registry,
        )
        self.co2_gauge = prometheus.Gauge(
            name='co2_ppm',
            desc='co2 sensor output',
            labels=['sensor'],
            registry=self.registry,
        )

    def update(self, m):
        self.temperature_gauge.labels('dht22').set(m.dht_temperature)
        self.temperature_gauge.labels('bme680').set(m.bme_temperature)
        self.humidity_gauge.labels('dht22').set(m.dht_humidity / 100.0)
        self.humidity_gauge.labels('bme680').set(m.bme_humidity / 100.0)
        self.pressure_gauge.labels('bme680').set(m.pressure)
        self.gas_resistance_gauge.labels('bme680').set(m.gas_resistance)
        self.indoor_air_quality_gauge.labels('bme680').set(m.indoor_air_quality)
        self.co2_gauge.labels('mhz19').set(m.co2)

    def serve(self, port=80):
        wlan = network.WLAN(network.STA_IF)
        ip = wlan.ifconfig()[0]
        print('binding server: {}:{}'.format(ip, port))

        self.router = prometheus.Router()
        self.router.register('GET', '/metrics', self.registry.handler)
        try:
            self.server = prometheus.start_http_server(port, address=ip)
        except OSError as err:
            if err.errno == 112:  # EADDRINUSE
                print(err)
                print('resetting device...')
                machine.reset()

        _thread.start_new_thread(self._accept_connections, ())

    def _accept_connections(self):
        while True:
            try:
                self.server.accept(self.router)
            except OSError as err:
                if err.errno == 116:  # ETIMEDOUT
                    continue
                print('error accepting request: {}'.format(err))
            except ValueError as err:
                print('error parsing request: {}'.format(err))
