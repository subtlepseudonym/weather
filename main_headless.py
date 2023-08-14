import dht, machine, time
import bme680, c8d, prometheus, sensors

s = sensors.Sensors(
    bme=bme680.BME680(2, 5),
    c8d=c8d.C8D(2),
)
time.sleep(2)
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
