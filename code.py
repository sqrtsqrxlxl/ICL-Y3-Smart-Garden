# This code is intended to be ran on Arduino Nano RP2040 Connect.

import time
import random
from os import getenv

import adafruit_connection_manager
import adafruit_requests
import board
import busio
import digitalio
import analogio
from digitalio import DigitalInOut
import adafruit_dht

from adafruit_esp32spi import adafruit_esp32spi
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

# ---- Credentials ----
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")
aio_username = getenv("ADAFRUIT_AIO_USERNAME")
aio_key = getenv("ADAFRUIT_AIO_KEY")

# ---- Declare every feed in one place ----
# "out" = board sends values up;  "in" = board reads values from dashboard.
FEEDS = {
    "moisture":    "out",
    "temperature": "out",
    "humidity":    "out",
    "hydraulic_pump": "out",
    "ph": "out",
    "status": "out",
}

# ---- ESP32 SPI setup (unchanged) ----
esp32_cs    = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

if "SCK1" in dir(board):
    spi = busio.SPI(board.SCK1, board.MOSI1, board.MISO1)
else:
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)

esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

pool        = adafruit_connection_manager.get_radio_socketpool(esp)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(esp)
requests    = adafruit_requests.Session(pool, ssl_context)

# ---- Wi-Fi ----
print("Connecting to Wi-Fi...")
while not esp.is_connected:
    try:
        esp.connect_AP(ssid, password)
    except OSError as e:
        print("  retrying:", e)
        continue
print("Connected:", esp.ap_info.ssid, "IP:", esp.ipv4_address)

# ---- Adafruit IO ----
io = IO_HTTP(aio_username, aio_key, requests)

# Verify/create each feed once, up front.
feeds = {}
for key in FEEDS:
    try:
        feeds[key] = io.get_feed(key)
    except AdafruitIO_RequestError:
        feeds[key] = io.create_new_feed(key)
    print("Ready:", feeds[key]["key"], "(", FEEDS[key], ")")

# ---- Local hardware ----
pump_hardware = digitalio.DigitalInOut(board.A0)
pump_hardware.direction = digitalio.Direction.OUTPUT
moisture_sensor = analogio.AnalogIn(board.A1)
ph_sensor = analogio.AnalogIn(board.A2)
dht_sensor = adafruit_dht.DHT11(board.D3) # DHT11 is used for both temperature and humidity.


def read_moisture():
    """Returns a calculated relative moisture level as measured by the sensor."""
    return moisture_sensor.value

def read_temperature():
    """Returns the Temperature in Celsius as measured by the sensor."""
    return dht_sensor.temperature

def read_humidity():
    """Returns the Humidity as measured by the sensor."""
    return dht_sensor.humidity

def read_ph():
    """Returns the pH level as measured by the sensor."""
    return ph_sensor.value

def pump_water():
    """Activates the pump for 10 seconds to water the herb, then turns it off."""
    pump_hardware.value = True
    time.sleep(10)
    pump_hardware.value = False
    return "Herb watered"

def get_status():
    """Returns a string indicating the system's operational status."""
    return "All good"

def get_health():
    """Returns a string indicating the health status of the herb based on sensor readings."""
    moisture = read_moisture()
    temperature = read_temperature()
    humidity = read_humidity()
    ph = read_ph()

    if moisture < 1000:
        return "Move me! My soil is too dry!"
    elif temperature > 30:
        return "Move me! I'm too hot!"
    elif humidity < 20:
        return "Move me! My humidity is too low!"
    else:
        return "I'm happy and healthy!"
    

SENSOR_READERS = {
    "moisture":    read_moisture,
    "temperature": read_temperature,
    "humidity":    read_humidity,
    "hydraulic_pump": pump_water,
    "ph": read_ph,
    "status": get_status,
    "health_status": get_health,
}

while True:
    try:
        # Send every "out" feed.
        for key, direction in FEEDS.items():
            if direction == "out":
                value = SENSOR_READERS[key]()
                io.send_data(feeds[key]["key"], value)
                print(f"  -> {key} = {value}")

        # TODO: A minigame function. Triggers as an alarm at a given time of the day.
        # When triggered, a piezoelectric buzzer will sound until the player successfully completes the minigame.

        # TODO: Sends an notification to the user if any of the sensor readings are outside the healthy range.
        # Implementation TBD (X? Discord? SMS? Email?).
    except Exception as e:
        print("IO error:", e)
        io.send_data(feeds["status"]["key"], 2) # 2 = error. Dashboard judgement logic: All good if status < 2.

    time.sleep(2)
