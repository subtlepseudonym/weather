import dht, machine
import bme680, display

screen = display.Display(1, 26, 15, 2, 4, 12)
d = dht.DHT22(machine.Pin(27))
bme = bme680.BME680(2, 5)

def update():
    d.measure()

    d_temp = d.temperature()
    b_temp = bme.temperature
    temperature = (d_temp + b_temp) / 2.0

    d_humid = d.humidity()
    b_humid = bme.humidity
    humidity = (d_humid + b_humid) / 2.0

    screen.update_values(
        pressure=bme.pressure,
        humidity=humidity,
        temperature=temperature,
        gas=bme.gas_resistance
    )
    screen.wake()
    screen.draw_buffer()
    screen.sleep()

update()
t0 = machine.Timer(0)
t0.init(period=300000, mode=machine.Timer.PERIODIC, callback=lambda t:update())
