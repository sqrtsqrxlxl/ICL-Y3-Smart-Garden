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

# Imports the memory minigame from minigame.py.
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

# This is the reconnection function in case there was a network failure.
# In practice, the ESP32's Wi-Fi connection was extremely unstable,
# In 80% of the time, the ESP32 module would fail to connect to arduino.
# Therefore this function is here to recover the program in case of network failure, without crashing the entire program.

# The network instability is not a code issue, but more likely either a hardware issue or a server-side issue with Adafruit IO.

# It is suggested that for smooth engineering and testing experience,
# Either the Arduino RP2040 Connect board should be replaced with a more stable one,
# Or another IoT platform with better server stability should be used instead of Adafruit IO.

def reconnect(retries=3):
    """Attempt to reset and reconnect the ESP32. If it fails after
    `retries` attempts, do a full microcontroller reset."""
    for attempt in range(1, retries + 1):
        try:
            print(f"Reconnect attempt {attempt}/{retries}...")
            esp.reset()           # hard-reset the SPI co-processor first
            time.sleep(1)
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
    while True:
        try:
            feeds[key] = io.get_feed(key)
            break
        except Exception as e:
            print("Unexpected error in key ", key, ": ", e)
            time.sleep(1)
    print("Ready:", feeds[key]["key"], "(", FEEDS[key], ")")

# ---- Local hardware ----
pump_hardware = digitalio.DigitalInOut(board.D12)
pump_hardware.direction = digitalio.Direction.OUTPUT
moisture_sensor = analogio.AnalogIn(board.A0)
ph_sensor = analogio.AnalogIn(board.A2)
dht_sensor = adafruit_dht.DHT11(board.A1) # DHT11 is used for both temperature and humidity.

# ---- Functions ----
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
    """Returns time since last watering in minutes and seconds"""
    elapsed_time = time.monotonic() - last_watered_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    return f"{minutes}:{seconds:02d}"

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

# ---- Global variables ----
ALARMS = [(8, 0)] # List of (hour, minute) tuples indicating when the minigame alarm should trigger.
WATER_INTERVAL = 60 * 60 # Water every 1 hour (3600 seconds)
last_watered_time = time.monotonic() - WATER_INTERVAL  # Initialize to allow immediate watering on startup

# ---- Main loop ----
while True:
    try:
        # Send sensor readings to Adafruit IO for each "out" feed.
        # So that the dashboard can display them and trigger automations based on them.

        # Currently, the notification function is achieved by Adafruit IO's "Action" panel. 
        # Whenever the "health-status" feed updates, and if it's not "I'm happy and healthy!", 
        # it sends a notification to the user with the content of the feed (which is the health status message).

        for key, direction in FEEDS.items():
            if direction == "out":
                value = SENSOR_READERS[key]()
                io.send_data(feeds[key]["key"], value)
                print(f"  -> {key} = {value}")

        # If the moisture level is low (i.e. the herb needs watering),
        # And if it's been more than WATER_INTERVAL seconds since the last watering,
        # trigger the pump and send a notification to the user.

        if read_moisture() < 0.5 and (time.monotonic() - last_watered_time > WATER_INTERVAL):
            pump_water()
            last_watered_time = time.monotonic()

        # A minigame function. Triggers as an alarm at a given time of the day.
        # When triggered, the player have to complete the minigame.

        now = time.localtime()
        for hour, minute in ALARMS:
            if now.tm_hour == hour and now.tm_minute == minute and (abs(now.tm_second) < 30 or abs(now.tm_second - 60) < 30): # crude way to ensure the alarm triggers for a few seconds, not just one loop iteration.
                print("Alarm! Wake up! Send a notification to the user...")
                memory_game()
                print("Minigame completed! Alarm deactivated.")

        # Sends an notification to the user if any of the sensor readings are outside the healthy range.
        # The print function is left here so that in the future it could be hooked up with python libraries or services
        # which support sending notifications to the user (e.g. Pushbullet, Twilio, Pushover, etc.)

        if not get_health_boolean():
            print("Sending health alert notification to user...")
            print(get_health())

    # Below are error handling blocks so that the Adruino can recover gracefully 
    # from common issues like network failures or sensor read errors, 
    # without crashing the entire program.

    except (OSError, TimeoutError) as e:
        # Likely an ESP32 SPI / WiFi failure — reconnect FIRST, then report status
        print("Network/ESP32 error:", e)
        reconnect()  # Reset ESP32 and reconnect; reboots board if unrecoverable
        try:
            io.send_data(feeds["status"]["key"], 2)
        except Exception as send_err:
            print("  could not report status after reconnect:", send_err)

    except RuntimeError as e:
        # DHT11 often throws RuntimeError on a bad read — just skip this cycle
        print("Sensor read error (skipping cycle):", e)
        try:
            io.send_data(feeds["status"]["key"], 2)
        except Exception as send_err:
            print("  could not report status:", send_err)

    except Exception as e:
        # Anything else unexpected — log it and reboot to be safe
        print("Unexpected error:", e)
        try:
            io.send_data(feeds["status"]["key"], 2)
        except Exception:
            pass
        time.sleep(2)
        microcontroller.reset()

    # Due to adafruit IO's rate limits, we can only send a certain number of updates per minute.
    # Currently it's twice every minute.

    time.sleep(30)

# Footnotes

# The connectivity was very poor throughout the development process,
# And in reality, we never got the program to run stably for more than 1 minute
# Without it crashing due to network issues.
# I have attempted to implement various error handling and reconnection strategies to mitigate this issue,
# But the underlying instability of the ESP32's Wi-Fi connection on this board made it very
# difficult to achieve a fully stable and smooth user experience.

# There were also issues with hardwares, especially the hydraulic pump,
# Which is extremely unstable and unreliable, not wishing to turn on 99% of the time,
# And how we turn it on is by fidgeting with the wires,
# Making the stability a complete mystery.

# Herbs purchased from supermarkets were normally overcrowded,
# And we should be notified that it would be ideal to transplant only one herb
# To a pot of our own, otherwise the herb would in theory die within a few days
# Due to overcrowding and competition for resources.
# Or on the contrary, the teaching assistant might want to transplant the herbs for the groups
# to ensure the herbs' survival.

# In reality, it would be suggested that this project should be 
# implemented on a more stable IoT platform, or with a more stable Wi-Fi module than the ESP32 on this board.