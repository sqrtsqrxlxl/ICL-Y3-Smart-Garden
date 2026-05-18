"""
pH meter for Arduino Nano RP2040 Connect (CircuitPython)
Port of the SEN0161 analog pH meter sample code.
"""

import time
import board
import analogio
import digitalio

# --- Configuration ---
SENSOR_PIN = board.A0
OFFSET = 2.64              # deviation compensation
SAMPLING_INTERVAL = 0++

+++++++.02   # 20 ms
PRINT_INTERVAL = 0.8       # 800 ms
ARRAY_LENGTH = 40          # number of samples to collect
VREF = 3.3                 # RP2040 ADC reference (was 5.0 on the Arduino Uno)
ADC_MAX = 65535            # CircuitPython presents ADC as 16-bit (was 1023 on Uno)

# --- Hardware setup ---
sensor = analogio.AnalogIn(SENSOR_PIN)
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT


def average_array(arr):
    """Average the array, throwing out the single highest and lowest values."""
    n = len(arr)
    if n <= 0:
        print("Error: empty array for averaging!")
        return 0
    if n < 5:
        return sum(arr) / n
    # Equivalent to the C++ version's min/max-trimmed mean, just more concise.
    return (sum(arr) - min(arr) - max(arr)) / (n - 2)


# --- State ---
ph_array = [0] * ARRAY_LENGTH
ph_index = 0
voltage = 0.0
ph_value = 0.0

sampling_time = time.monotonic()
print_time = time.monotonic()

print("pH meter experiment!")

while True:
    now = time.monotonic()

    if now - sampling_time > SAMPLING_INTERVAL:
        ph_array[ph_index] = sensor.value
        ph_index = (ph_index + 1) % ARRAY_LENGTH
        avg = average_array(ph_array)
        voltage = avg * VREF / ADC_MAX
        ph_value = 3.5 * voltage + OFFSET
        sampling_time = now

    if now - print_time > PRINT_INTERVAL:
        print("Voltage: {:.2f}    pH value: {:.2f}".format(voltage, ph_value))
        led.value = not led.value
        print_time = now
