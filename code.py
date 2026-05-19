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
import microcontroller
from minigame import memory_game

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
    "hydraulic-pump": "out",
    "ph": "out",
    "status": "out",
    "health-status": "out",
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
def connect_wifi():
    print("Connecting to Wi-Fi...")
    while not esp.is_connected:
        try:
            esp.connect_AP(ssid, password)
        except OSError as e:
            print("  retrying:", e)
            continue
    print("Connected:", esp.ap_info.ssid, "IP:", esp.ipv4_address)

def reconnect(retries=3):
    """Attempt to reset and reconnect the ESP32. If it fails after
    `retries` attempts, do a full microcontroller reset."""
    for attempt in range(1, retries + 1):
        try:
            print(f"Reconnect attempt {attempt}/{retries}...")
            connect_wifi()
            return True  # Success
        except Exception as e:
            print("  failed:", e)
            time.sleep(2)
    print("ESP32 unrecoverable. Rebooting microcontroller...")
    time.sleep(1)
    microcontroller.reset()  # Full board reset — restarts code.py from scratch

connect_wifi()

# ---- Adafruit IO ----
io = IO_HTTP(aio_username, aio_key, requests)

# Verify/create each feed once, up front.
feeds = {}
for key in FEEDS:
    try:
        feeds[key] = io.get_feed(key)
    except Exception as e:
        print("Unexpected error in key ", key, ": ", e)
    print("Ready:", feeds[key]["key"], "(", FEEDS[key], ")")

# ---- Local hardware ----
pump_hardware = digitalio.DigitalInOut(board.D12)
pump_hardware.direction = digitalio.Direction.OUTPUT
moisture_sensor = analogio.AnalogIn(board.A0)
ph_sensor = analogio.AnalogIn(board.A2)
dht_sensor = adafruit_dht.DHT11(board.A1) # DHT11 is used for both temperature and humidity.


def read_moisture():
    """Returns a calculated relative moisture level as measured by the sensor."""
    moisture_relative = moisture_sensor.value * 3.3 / 65535  # Convert raw sensor value to voltage
    moisture = (moisture_relative + 0.03) / 1.92 
    return round(moisture, 2)

def read_temperature():
    """Returns the Temperature in Celsius as measured by the sensor."""
    return dht_sensor.temperature

def read_humidity():
    """Returns the Humidity as measured by the sensor."""
    return dht_sensor.humidity

def read_ph():
    """Returns the pH level as measured by the sensor."""
    pH_sensor = ph_sensor.value
    # Convert the raw sensor value to a pH level (this is a simplified example;
    pH = (pH_sensor * 3.3 / 65535) * 3.5 + 2.64  # Scale to 0-14
    return round(pH, 2)

def pump_water():
    """Activates the pump for 10 seconds to water the herb, then turns it off."""
    pump_hardware.value = True
    time.sleep(10)
    pump_hardware.value = False
    return "Herb watered"
    
def pump_status():
    """Returns pump status"""
    return "ON" if pump_hardware.value else "OFF"

def get_status():
    """Returns a string indicating the system's operational status."""
    return 0

def get_health():
    """Returns a string indicating the health status of the herb based on sensor readings."""
    moisture = read_moisture()
    temperature = read_temperature()
    humidity = read_humidity()
    ph = read_ph()
    return_string = []
    status_boolean = not (moisture < 0.5 or moisture > 0.7 or temperature > 24 or temperature < 15 or humidity < 40 or humidity > 60 or ph < 5.5 or ph > 7.5)


    if moisture < 0.5:
        return_string.append("Water me! My soil is too dry!")
    if moisture > 0.7:
        return_string.append("Don't water me! My soil is too wet!") 
    if temperature > 24:
        return_string.append("Move me! I'm too hot!")
    if temperature < 15:
        return_string.append("Move me! I'm too cold!")
    if humidity < 40:
        return_string.append("Move me! My humidity is too low!")
    if humidity > 60:
        return_string.append("Move me! My humidity is too high!")
    if ph < 5.5:
        return_string.append("Adjust my soil! I'm too acidic!")
    if ph > 7.5:
        return_string.append("Adjust my soil! I'm too alkaline!")
    if status_boolean:
        return_string.append("I'm happy and healthy!")

    return_message = ""

    for messages in return_string:
        return_message += messages + "\n"

    return_message = return_message.strip() # Remove trailing newline
    return return_message

def get_health_boolean():
    """Returns a boolean indicating whether the herb is healthy based on sensor readings."""
    moisture = read_moisture()
    temperature = read_temperature()
    humidity = read_humidity()
    ph = read_ph()

    status_boolean = not (moisture < 0.5 or moisture > 0.7 or temperature > 24 or temperature < 15 or humidity < 40 or humidity > 60 or ph < 5.5 or ph > 7.5)
    return status_boolean

SENSOR_READERS = {
    "moisture":    read_moisture,
    "temperature": read_temperature,
    "humidity":    read_humidity,
    "hydraulic-pump": pump_status,
    "ph": read_ph,
    "status": get_status,
    "health-status": get_health,
}

ALARMS = [(8, 0)] # List of (hour, minute) tuples indicating when the minigame alarm should trigger.
WATER_INTERVAL = 60 * 60 # Water every 1 hour (3600 seconds)
last_watered_time = time.monotonic() - WATER_INTERVAL  # Initialize to allow immediate watering on startup

while True:
    try:
        # Send every "out" feed.
        for key, direction in FEEDS.items():
            if direction == "out":
                value = SENSOR_READERS[key]()
                io.send_data(feeds[key]["key"], value)
                print(f"  -> {key} = {value}")

        # If the moisture level is low (i.e. the herb needs watering),
        # trigger the pump and send a notification to the user.

        if read_moisture() < 0.5 and (time.monotonic() - last_watered_time > WATER_INTERVAL):
            pump_water()
            last_watered_time = time.monotonic()

        # TODO: A minigame function. Triggers as an alarm at a given time of the day.
        # When triggered, a piezoelectric buzzer will sound until the player successfully completes the minigame.

        now = time.localtime()
        for hour, minute in ALARMS:
            if now.tm_hour == hour and now.tm_minute == minute and (abs(now.tm_second) < 30 or abs(now.tm_second - 60) < 30): # crude way to ensure the alarm triggers for a few seconds, not just one loop iteration.
                print("Alarm! Wake up! Send a notification to the user... (TODO)")
                memory_game()
                print("Minigame completed! Alarm deactivated.")

        # TODO: Sends an notification to the user if any of the sensor readings are outside the healthy range.
        # Implementation TBD (X? Discord? SMS? Email?).

        if not get_health_boolean():
            print("Sending health alert notification to user... (TODO)")
            print(get_health())

    except OSError as e:
        # Likely an ESP32 SPI / WiFi failure
        print("Network/ESP32 error:", e)
        io.send_data(feeds["status"]["key"], 2)
        reconnect()  # Reset ESP32 and reconnect; reboots board if unrecoverable

    except RuntimeError as e:
        # DHT11 often throws RuntimeError on a bad read — just skip this cycle
        io.send_data(feeds["status"]["key"], 2)
        print("Sensor read error (skipping cycle):", e)

    except Exception as e:
        # Anything else unexpected — log it and reboot to be safe
        io.send_data(feeds["status"]["key"], 2)
        print("Unexpected error:", e)
        time.sleep(2)
        microcontroller.reset()

    time.sleep(30)
