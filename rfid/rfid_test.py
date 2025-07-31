import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

reader = SimpleMFRC522()

try:
    print('Coloca tu tarjeta cerca del sensor')
    id, text = reader.read()
    print('ID: %s\nText: %s' % (id,text))
finally:
    GPIO.cleanup()
