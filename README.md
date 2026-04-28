# 🌿 AI Plant Review + Moisture

A real-time plant monitoring dashboard powered by Gemini AI, Raspberry Pi, and soil moisture sensors. This project captures photos and soil moisture data, uploads them to Firebase, and uses Gemini AI to analyze overall plant health.

## 🚀 Features

- **Visual Health Analysis**: Gemini AI assesses leaf color, texture, and morphology.
- **Moisture Monitoring**: Integrates capacitive soil moisture sensors (ADS1115) for real-time hydration tracking.
- **Uplink History**: View snapshots and telemetry data over time.
- **Automated Alerts**: Visual indicators for "Critical: Dry" or "Optimal" states.

## 🛠 Raspberry Pi & Sensor Setup

### 1. Required Packages
Ensure your Raspberry Pi has the necessary tools installed. For the moisture sensor, we use the `adafruit-ads1x15` library.

```bash
sudo apt-get update
sudo apt-get install curl coreutils fswebcam python3 python3-pip
pip3 install requests adafruit-circuitpython-ads1x15
```

### 2. Hardware Wiring (Raspberry Pi 5)

To maintain signal integrity and protect your Pi 5, we will use 3.3V logic for the entire circuit.

#### 1. Raspberry Pi 5 to ADS1115 (I2C Interface)
Connect the ADC module to the Pi's 40-pin header using the standard I2C pins.

| ADS1115 Pin | Raspberry Pi 5 Pin | Function |
|-------------|--------------------|----------|
| VDD         | Pin 1 (3.3V)       | Power supply (Logic-level matched) |
| GND         | Pin 6 (GND)        | Common ground |
| SCL         | Pin 5 (GPIO 3)     | I2C Serial Clock |
| SDA         | Pin 3 (GPIO 2)     | I2C Serial Data |
| ADDR        | Pin 9 (GND)        | Sets I2C Address to 0x48 |

#### 2. ADS1115 to Capacitive Moisture Sensor
The capacitive sensor typically has three pins: VCC, GND, and AOUT (Analog Output).

| Sensor Pin | Connection Point | Notes |
|------------|------------------|-------|
| VCC        | Pi Pin 17 (3.3V) | Keeps analog output within 0-3.3V range. |
| GND        | Pi Pin 14 (GND)  | Shared ground with ADC and Pi. |
| AOUT       | ADS1115 A0       | Connect to the first ADC channel. |

![Wiring Diagram](https://raw.githubusercontent.com/carolinedunn/AI-Plant-Review-with-Moisture-Sensor/0b2c8188101a97f356bd06560665bf2a61b45bd0/plant-moisture-sensor-ADS1115_bb.png)

### 3. Testing & Calibration

Before scheduling the automated script, use this script to test your sensor and find your `V_DRY` and `V_WET` values for calibration.

1. Create the test script: `nano ~/PlantPhotos/test_sensor.py`
2. Paste the following:

```python
import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Initialize I2C
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize ADC
ads = ADS.ADS1115(i2c)
ads.gain = 1

# Using '0' directly instead of 'ADS.P0' bypasses the attribute error.
# Channel indices: 0 = A0, 1 = A1, 2 = A2, 3 = A3
chan = AnalogIn(ads, 0)

print("--- Starting Real-Time Moisture Monitor (V3.13 Fix) ---")
print("Press Ctrl+C to stop.")
print("{:>10}\t{:>10}".format("Raw Value", "Voltage"))

try:
    while True:
        # Read the raw value and voltage
        raw_val = chan.value
        volts = chan.voltage
        
        print("{:>10}\t{:>10.3f}V".format(raw_val, volts))
        time.sleep(1)

except KeyboardInterrupt:
    print("\nMonitor stopped.")
except Exception as e:
    print(f"\nHardware Error: {e}")
```

3. **Calibrate**: Note the voltage when the sensor is in open air (`V_DRY`) and when fully submerged in water up to the safe line (`V_WET`). Update these values in your `upload.py` script.

---

## 📸 Automated Upload Script (`upload.py`)

This script handles both the moisture reading and the image upload. It calculates a moisture percentage based on voltage calibration.

1. Create the file: `nano ~/PlantPhotos/upload.py`
2. Paste the script below (**Replace the placeholders** with your Firebase values):

```python
import base64
import requests
import os
import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# --- CONFIGURATION ---
# Find these in Firebase Console -> Project Settings -> General
API_KEY = "<YOUR_FIREBASE_API_KEY>"
PROJECT_ID = "<YOUR_PROJECT_ID>" 
# DB_ID is usually "(default)"
DB_ID = "(default)"
# SECRET must match the UPLOAD_SECRET in your dashboard settings
SECRET = "<YOUR_UPLOAD_SECRET>"
IMAGE_DIR = os.path.expanduser("~/PlantPhotos")

# --- CALIBRATION CONSTANTS ---
# Tune these based on your specific sensor (measure voltage in air vs water)
V_DRY = 2.8 
V_WET = 1.8

def get_moisture_data():
    """Reads the ADS1115 and returns calculated percentage."""
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        ads.gain = 1
        chan = AnalogIn(ads, 0) # P0

        voltage = chan.voltage
        # Linear mapping formula
        percentage = ((V_DRY - voltage) / (V_DRY - V_WET)) * 100
        final_percent = max(0, min(100, round(percentage, 1)))

        return final_percent, round(voltage, 3)
    except Exception as e:
        print(f"Hardware Error: {e}")
        return 0.0, 0.0

def get_latest_image():
    files = [os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR) if f.endswith('.jpg')]
    return max(files, key=os.path.getctime) if files else None

# 1. Gather Data
moisture_val, voltage_val = get_moisture_data()
latest = get_latest_image()

if not latest:
    print("No photos found.")
    exit()

with open(latest, "rb") as img_file:
    b64_string = base64.b64encode(img_file.read()).decode('utf-8')

# 2. Upload to Firestore
url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/{DB_ID}/documents/snapshots?key={API_KEY}"
payload = {
    "fields": {
        "image": {"stringValue": b64_string},
        "timestamp": {"integerValue": str(int(time.time() * 1000))},
        "secret": {"stringValue": SECRET},
        "moisture": {"doubleValue": moisture_val},
        "voltage": {"doubleValue": voltage_val}
    }
}

response = requests.post(url, json=payload)
if response.status_code == 200:
    print(f"✅ Uploaded: {os.path.basename(latest)} | Moisture: {moisture_val}%")
else:
    print(f"❌ Error {response.status_code}: {response.text}")
```

## 📋 Scheduling (Crontab)

Run `crontab -e` and add these tasks:

```bash
# Capture photo every 30 mins
*/30 7-19 * * * /usr/bin/python3 ~/PlantPhotos/takephoto.py

# Upload photo + moisture every 2 hours
2 7,9,11,13,15,17,19 * * * /usr/bin/python3 ~/PlantPhotos/upload.py

# Cleanup photos older than 2 days
0 0 * * * find ~/PlantPhotos/ -name "*.jpg" -type f -mtime +2 -delete
```

---

## 📚 A Woman’s Guide to Winning in Tech

If you enjoyed this repo, check out my book, **A Woman’s Guide to Winning in Tech.** This book blends sharp humor with practical career strategies to help women navigate tech on their own terms—without changing who they are. Available on Amazon, Bookshop.org, Barnes & Noble, and IngramSpark.

- [Book Website](https://winningintech.com/) 
- [Amazon](https://amzn.to/3YxHVO7)
- [Instagram](https://www.instagram.com/winning.tech)
- [Facebook](https://www.facebook.com/winningintech)
