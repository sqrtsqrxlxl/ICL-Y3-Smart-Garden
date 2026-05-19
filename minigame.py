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

SEQUENCE_LENGTH = 7
FLASH_TIME = 0.4
DEBOUNCE_TIME = 0.05

# -------------------------
# FUNCTIONS
# -------------------------

def flash(led):
    led.value = True
    time.sleep(FLASH_TIME)
    led.value = False
    time.sleep(0.2)

def startup_flash():
    for i in range(2):
        for led in leds:
            led.value = True

        time.sleep(0.5)

        for led in leds:
            led.value = False

        time.sleep(0.5)

def generate_sequence():
    sequence = []

    for i in range(SEQUENCE_LENGTH):
        sequence.append(led_colors[random.randint(0, 3)])

    return sequence

def show_sequence(sequence):
    for color in sequence:
        flash(leds[led_colors.index(color)])

def get_player_input():
    presses = []

    while len(presses) < SEQUENCE_LENGTH:

        for i, button in enumerate(buttons):

            if button.value == False: # Button is pressed

                presses.append(led_colors[i])

                # Flash corresponding LED when pressed
                flash(leds[i])

                print("Pressed:", led_colors[i])

                # Debounce
                # time.sleep(DEBOUNCE_TIME)

                # Wait until button released
                while not button.value:
                    pass

    return presses

# -------------------------
# MAIN GAME LOOP
# -------------------------

def memory_game():

    while True:

        correct = False

        # Generate new sequence
        sequence = generate_sequence()

        print("Sequence:", sequence)

        startup_flash()

        # Show pattern
        show_sequence(sequence)

        # Get player answer
        player_input = get_player_input()

        print("Player:", player_input)

        # Check answer
        if player_input == sequence:

            print("YOU PASS")

            # Success flash
            for i in range(3):
                for led in leds:
                    led.value = True

                time.sleep(0.2)

                for led in leds:
                    led.value = False

                time.sleep(0.2)

            break

        else:

            print("FAIL")

            # Failure flash
            for i in range(3):
                led0.value = True
                time.sleep(0.2)
                led0.value = False
                time.sleep(0.2)

        # Pause before next round
        time.sleep(2)
        
        
memory_game()
