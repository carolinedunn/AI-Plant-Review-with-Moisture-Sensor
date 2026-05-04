import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
#from adafruit_ads1x15.ads1115 import P0

# Initialize the I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create the ADC object using the I2C bus
ads = ADS.ADS1115(i2c)

# Create a single-ended input on channel 0
chan = AnalogIn(ads, 0)

# Set the gain to 1 for a range of +/- 4.096V 
# (Safe for 3.3V capacitive sensors)
ads.gain = 1

print("--- Starting Real-Time Moisture Monitor ---")
print("Press Ctrl+C to stop.")
print("{:>5}\t{:>5}".format("Raw Value", "Voltage"))

try:
    while True:
        # Read the raw 16-bit value and the voltage
        raw_val = chan.value
        volts = chan.voltage

        print("{:>5}\t{:>5.3f}V".format(raw_val, volts))
        # Wait 1 second before the next reading
        time.sleep(1)

except KeyboardInterrupt:
    print("\nMonitor stopped by user.")
