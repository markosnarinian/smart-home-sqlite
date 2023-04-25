import RPi.GPIO as GPIO
from RPi.GPIO import setwarnings
from RPi.GPIO import setmode
from RPi.GPIO import setup
from RPi.GPIO import output
from RPi.GPIO import input
from RPi.GPIO import BCM
from RPi.GPIO import OUT
from RPi.GPIO import LOW
from RPi.GPIO import HIGH
from time import sleep

setwarnings(False)
setmode(BCM)
setup(11, OUT)
setup(2, OUT)

delay = 0.1

if input(2) == 0:
    output(2, HIGH)
    sleep(delay)
    output(2, LOW)
    sleep(delay)
    output(2, HIGH)
    sleep(delay)
    output(2, LOW)
elif input(2) == 1:
    output(2, LOW)
    sleep(delay)
    output(2, HIGH)
    sleep(delay)
    output(2, LOW)
    sleep(delay)
    output(2, HIGH)
