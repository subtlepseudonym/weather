import dht, machine
import bme680, mhz19, prometheus, sensors

s = sensors.Sensors(
    dht=dht.DHT22(machine.Pin(27)),
    bme=bme680.BME680(2, 5),
    mhz=mhz19.MHZ19(2),
)
s.update()

# set up prometheus metrics
p = prometheus.Prometheus()
p.update(s)
p.serve()  # may call machine.reset on error

PROMETHEUS_INTERVAL = 15000  # 15sec
def update(t):
    s.update()
    p.update(s)
    s.print()

t0 = machine.Timer(0)
t0.init(period=PROMETHEUS_INTERVAL, mode=machine.Timer.PERIODIC, callback=update)
