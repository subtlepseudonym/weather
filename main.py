import dht, machine, network, socket, _thread
import bme680, display
import prometheus_express as prometheus

screen = display.Display(1, 26, 15, 2, 4, 12)
d = dht.DHT22(machine.Pin(27))
bme = bme680.BME680(2, 5)

registry = prometheus.CollectorRegistry(namespace='weather')
temperature_gauge = prometheus.Gauge(
    name='temperature_celsius',
    desc='temperature sensor output',
    labels=['sensor'],
    registry=registry,
)
humidity_gauge = prometheus.Gauge(
    name='humidity_ratio',
    desc='humidity sensor output',
    labels=['sensor'],
    registry=registry,
)
pressure_gauge = prometheus.Gauge(
    name='pressure_hectopascals',
    desc='atmospheric pressure sensor output',
    labels=['sensor'],
    registry=registry,
)
gas_resistance_gauge = prometheus.Gauge(
    name='gas_resistance_ohms',
    desc='metal-oxide gas sensor resistance value',
    labels=['sensor'],
    registry=registry,
)
indoor_air_quality_gauge = prometheus.Gauge(
    name='indoor_air_quality_score',
    desc='score for indoor air quality ranging from 0-500',
    labels=['sensor'],
    registry=registry,
)

def measure():
    d.measure()

    d_temp = d.temperature()
    b_temp = bme.temperature
    temperature = (d_temp + b_temp) / 2.0

    d_humid = d.humidity()
    b_humid = bme.humidity
    humidity = (d_humid + b_humid) / 2.0

    return type('', (object,), {
        "dht_temperature": d_temp,
        "dht_humidity": d_humid,
        "bme_temperature": b_temp,
        "bme_humidity": b_humid,
        "temperature": temperature,
        "humidity": humidity,
        "pressure": bme.pressure,
        "indoor_air_quality": bme.indoor_air_quality,
        "gas_resistance": bme.gas_resistance,
    })

def print_measurements(m):
    print('--------')
    print(f'dht temp:  {m.dht_temperature:6.1f} °C')
    print(f'bme temp:  {m.bme_temperature:6.1f} °C')
    print(f'dht humid: {m.dht_humidity:6.1f} %rh')
    print(f'bme humid: {m.bme_humidity:6.1f} %rh')
    print(f'pressure:  {m.pressure:6.0f} hpa')
    print(f'gas res:   {m.gas_resistance:6.0f} ohm')
    print(f'iaq score: {m.indoor_air_quality:6.0f}')
    print('--------')

def update_metrics():
    m = measure()

    temperature_gauge.labels('dht22').set(m.dht_temperature)
    temperature_gauge.labels('bme680').set(m.bme_temperature)
    humidity_gauge.labels('dht22').set(m.dht_humidity / 100.0)
    humidity_gauge.labels('bme680').set(m.bme_humidity / 100.0)
    pressure_gauge.labels('bme680').set(m.pressure)
    indoor_air_quality_gauge.labels('bme680').set(m.indoor_air_quality)
    gas_resistance_gauge.labels('bme680').set(m.gas_resistance)

def update_screen():
    m = measure()
    print_measurements(m)

    screen.update_values(
        iaq=m.indoor_air_quality,
        temperature=m.temperature,
        humidity=m.humidity,
        gas=m.gas_resistance,
        pressure=m.pressure,
    )
    screen.wake()
    screen.draw_buffer()
    screen.sleep()

# set up prometheus server
wlan = network.WLAN(network.STA_IF)
ip = wlan.ifconfig()[0]
port = 80
print('binding server: {}:{}'.format(ip, port))

router = prometheus.Router()
router.register('GET', '/metrics', registry.handler)
try:
    server = prometheus.start_http_server(port, address=ip)
except OSError as err:
    if err.errno == 112:  # EADDRINUSE
        print(err)
        print('resetting device...')
        machine.reset()

def accept_connections():
    while True:
        try:
            server.accept(router)
        except OSError as err:
            if err.errno == 116:  # ETIMEDOUT
                continue
            print('error accepting request: {}'.format(err))
        except ValueError as err:
            print('error parsing request: {}'.format(err))

_thread.start_new_thread(accept_connections, ())

# update screen every 5m
update_screen()
t0 = machine.Timer(0)
t0.init(period=300000, mode=machine.Timer.PERIODIC, callback=lambda t:update_screen())

# update metrics every 30s
update_metrics()
t1 = machine.Timer(1)
t1.init(period=30000, mode=machine.Timer.PERIODIC, callback=lambda t:update_metrics())
