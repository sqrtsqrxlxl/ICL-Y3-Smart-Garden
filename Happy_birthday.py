
# 在这里写上你的代码 :-)
import time
import board
import pwmio

TONE_FREQ = [
    392, 392, 440, 392, 523, 494,
    392, 392, 440, 392, 587, 523,
    392, 392, 784, 659, 523, 494,
    440, 698, 698, 659, 523, 587, 523
]

TONE_TIME = [0.1875, 0.0625, 0.25, 0.25, 0.25, 0.5, 0.1875, 0.0625, 0.25, 0.25, 0.25, 0.5, 0.1875, 0.0625, 0.25, 0.25, 0.25, 0.25, 0.25, 0.1875, 0.0625, 0.25, 0.25, 0.25, 0.5]

G = pwmio.PWMOut(board.A0)
B = pwmio.PWMOut(board.A1)
R = pwmio.PWMOut(board.A2)
Y = pwmio.PWMOut(board.A3)
W = pwmio.PWMOut(board.D3)

TONE_LED = [G,G,B,R,Y,W,G,G,B,R,Y,W,G,G,B,R,Y,W,W,G,G,B,R,Y,W]

buzzer = pwmio.PWMOut(board.D2, variable_frequency=True)



ON = 2**15
OFF = 0

while True:
    for i in range(len(TONE_FREQ)):

        buzzer.frequency = TONE_FREQ[i]
        buzzer.duty_cycle = ON

        led_current = TONE_LED[i]

        led_current.duty_cycle = 65535

        time.sleep(TONE_TIME[i])

        buzzer.duty_cycle = OFF
        led_current.duty_cycle = 0

        time.sleep(0.1)
