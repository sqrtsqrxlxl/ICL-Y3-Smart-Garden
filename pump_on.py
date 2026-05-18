import board
import busio
import digitalio
import analogio

pump = digitalio.DigitalInOut(board.A0)
pump.direction = digitalio.Direction.INPUT

while True:
    pump.value = True