"""Guava orchard monitoring - reconstructed MicroPython Wokwi demo.
This is NOT the original coursework source code.
"""
from machine import Pin, ADC, PWM, time_pulse_us
import dht
import time

TEMP_WARNING_C = 35
SOIL_DRY_THRESHOLD = 40  # percent, potentiometer mapping for simulation
LOW_WATER_CM = 20        # sensor-to-water distance; larger means less water

sensor = dht.DHT22(Pin(15))
soil = ADC(Pin(34))
soil.atten(ADC.ATTN_11DB)
servo = PWM(Pin(18), freq=50)
trig = Pin(16, Pin.OUT)
echo = Pin(17, Pin.IN)
led_r = Pin(5, Pin.OUT)
led_g = Pin(4, Pin.OUT)
led_b = Pin(2, Pin.OUT)
rows = [Pin(p, Pin.OUT, value=1) for p in (13, 12, 14, 27)]
cols = [Pin(p, Pin.IN, Pin.PULL_UP) for p in (26, 25, 33, 32)]
KEYS = ('123A', '456B', '789C', '*0#D')
mode = 'AUTO'
manual_open = False
valve_open = False
last_key = None


def set_servo(angle):
    # SG90 ~0.5-2.5ms pulse at 50Hz, duty_u16: 1638-8192
    pulse_us = 500 + int(angle * 2000 / 180)
    servo.duty_u16(int(pulse_us * 65535 / 20000))


def set_valve(opened):
    global valve_open
    if opened != valve_open:
        set_servo(90 if opened else 0)
        valve_open = opened


def set_led(red=False, green=False, blue=False):
    led_r.value(int(red))
    led_g.value(int(green))
    led_b.value(int(blue))


def water_distance_cm():
    trig.off()
    time.sleep_us(2)
    trig.on()
    time.sleep_us(10)
    trig.off()
    try:
        pulse = time_pulse_us(echo, 1, 30000)
        if pulse < 0:
            return None
        return pulse / 58.0
    except OSError:
        return None


def scan_key():
    for i, row in enumerate(rows):
        row.off()
        time.sleep_us(50)
        for j, col in enumerate(cols):
            if not col.value():
                row.on()
                return KEYS[i][j]
        row.on()
    return None


def handle_key(key):
    global mode, manual_open
    if key == 'A':
        mode = 'AUTO'
    elif key == 'B':
        mode = 'MANUAL'
        manual_open = False
    elif key == '1' and mode == 'MANUAL':
        manual_open = True
    elif key == '0' and mode == 'MANUAL':
        manual_open = False


set_servo(0)
set_led(blue=True)
print('Guava orchard simulation ready. A=auto B=manual 1=open 0=close')
last_measure = time.ticks_ms() - 3000
while True:
    key = scan_key()
    if key and key != last_key:
        handle_key(key)
        print('Key:', key, 'Mode:', mode)
    last_key = key

    if time.ticks_diff(time.ticks_ms(), last_measure) >= 2500:
        last_measure = time.ticks_ms()
        try:
            sensor.measure()
            temperature = sensor.temperature()
            humidity = sensor.humidity()
        except OSError:
            temperature = None
            humidity = None

        # This mapping is for the Wokwi potentiometer, NOT a calibrated soil sensor.
        raw = soil.read()
        soil_percent = round(raw * 100 / 4095)
        distance = water_distance_cm()
        water_low = distance is None or distance >= LOW_WATER_CM
        dry = soil_percent < SOIL_DRY_THRESHOLD
        hot = temperature is not None and temperature >= TEMP_WARNING_C

        desired = (dry if mode == 'AUTO' else manual_open) and not water_low
        set_valve(desired)
        if water_low:
            set_led(red=True)
        elif hot:
            set_led(red=True, green=True)  # yellow
        elif valve_open:
            set_led(green=True)
        else:
            set_led(blue=True)

        print('Mode={} Temp={}C Humidity={}% Soil={}%(raw={}) WaterDistance={}cm LowWater={} Valve={}'.format(
            mode, temperature, humidity, soil_percent, raw,
            None if distance is None else round(distance, 1), water_low,
            'OPEN' if valve_open else 'CLOSED'))
    time.sleep_ms(60)
