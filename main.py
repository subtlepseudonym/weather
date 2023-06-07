import dht, machine
import bme680, display, prometheus, sensors

d = dht.DHT22(machine.Pin(27))
bme = bme680.BME680(2, 5)
s = sensors.Sensors(d, bme)
s.update()

# set up prometheus metrics
p = prometheus.Prometheus()
p.update(s)
p.serve()  # may call machine.reset on error

# set up e-ink display
screen = display.Display(1, 26, 15, 2, 4, 12)
screen.update(s)

PROMETHEUS_INTERVAL = 15000  # 15sec
SCREEN_INTERVAL = 300000  # 5min

# helper class for maintaining loop count
# overengineered, but beats maintaining thread locks for sensors access
class Updater():
    def __init__(self):
        self.count = 0
        self.screen_interval = SCREEN_INTERVAL
        self.prometheus_interval = PROMETHEUS_INTERVAL

    def update(self):
        s.update()
        p.update(s)

        self.count += 1
        if self.count % (self.screen_interval / self.prometheus_interval) == 0:
            s.print()
            screen.update(s)

updater = Updater()
t0 = machine.Timer(0)
t0.init(period=PROMETHEUS_INTERVAL, mode=machine.Timer.PERIODIC, callback=lambda t:updater.update())
