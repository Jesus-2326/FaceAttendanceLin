import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

reader = SimpleMFRC522()

try: 
    data_to_write = "24, JESUS MARTINEZ ARELLANO"

    print('Coloca la tarjeta cerca del sensor para sobre escribirlo')
    reader.write(data_to_write)
    print('Data written to the card successfully!')
finally:
    GPIO.cleanup()