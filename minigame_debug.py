import board
import time
import digitalio
from digitalio import DigitalInOut, Direction, Pull
import random

# -------------------------
# LED SETUP
# -------------------------

led0 = digitalio.DigitalInOut(board.D5)
led0.direction = digitalio.Direction.OUTPUT

led1 = digitalio.DigitalInOut(board.D4)
led1.direction = digitalio.Direction.OUTPUT

led2 = digitalio.DigitalInOut(board.D3)
led2.direction = digitalio.Direction.OUTPUT

led3 = digitalio.DigitalInOut(board.D2)
led3.direction = digitalio.Direction.OUTPUT

leds = [led0, led1, led2, led3]
led_colors = ["b", "g", "y", "r"] # blue, green, yellow, red

# -------------------------
# BUTTON SETUP
# -------------------------

btn0 = DigitalInOut(board.D6)
btn0.direction = Direction.INPUT
btn0.pull = Pull.UP

btn1 = DigitalInOut(board.D7)
btn1.direction = Direction.INPUT
btn1.pull = Pull.UP

btn2 = DigitalInOut(board.D8)
btn2.direction = Direction.INPUT
btn2.pull = Pull.UP

btn3 = DigitalInOut(board.D9)
btn3.direction = Direction.INPUT
btn3.pull = Pull.UP

buttons = [btn0, btn1, btn2, btn3]

# -------------------------
# SETTINGS
# -------------------------

def buttons_pressed():
    return [not btn.value for btn in buttons]


# -------------------------
# MAIN GAME LOOP
# -------------------------

while True:

    print(buttons_pressed())

    # Pause before next round
    time.sleep(1)