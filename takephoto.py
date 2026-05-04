import subprocess
import os
import datetime
import shutil

# --- CONFIGURATION ---
USE_PI_CAMERA = False #Set to False for webcam, set to True for Pi Camera
IMAGE_DIR = os.path.expanduser("~/PlantPhotos")
# Reduced resolution for the Pi Zero to save processing time/RAM
RESOLUTION_W = "800"
RESOLUTION_H = "800"

def get_camera_command():
    """Detects whether to use rpicam-still or libcamera-still."""
    if shutil.which("rpicam-still"):
        return "rpicam-still"
    elif shutil.which("libcamera-still"):
        return "libcamera-still"
    return None

def is_camera_connected():
    """Checks if the system actually sees a camera module."""
    try:
        # Check for both versions of the hello/list command
        cmd = "rpicam-hello" if shutil.which("rpicam-hello") else "libcamera-hello"
        result = subprocess.run([cmd, "--list-cameras"], capture_output=True, text=True)
        return "Available cameras" in result.stdout and "- " in result.stdout
    except:
        return False

def ensure_directory():
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)

def capture_image():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"{timestamp}.jpg"
    filepath = os.path.join(IMAGE_DIR, filename)

    if USE_PI_CAMERA:
        if not is_camera_connected():
            print("--- HARDWARE ERROR ---")
            print("No camera detected. Please check your ribbon cable orientation.")
            print("Silver contacts should face the PCB on the Pi Zero.")
            return None

        cmd = get_camera_command()
        print(f"Capturing with {cmd} to {filename}...")
        try:
            # -t 2000: Essential for Pi Zero auto-exposure
            subprocess.run([
                cmd,
                "--nopreview",
                "-t", "2000",
                "--width", RESOLUTION_W,
                "--height", RESOLUTION_H,
                "-o", filepath
            ], check=True)
            return filepath
        except subprocess.CalledProcessError as e:
            print(f"Capture Command Failed: {e}")
            return None
    else:
        # USB Webcam logic
        if not shutil.which("fswebcam"):
            print("Error: fswebcam not found.")
            return None
        try:
            subprocess.run(["fswebcam", "-r", f"{RESOLUTION_W}x{RESOLUTION_H}", "-S", "20", "--no-banner", filepath], check=True)
            return filepath
        except subprocess.CalledProcessError:
            return None

if __name__ == "__main__":
    ensure_directory()
    saved_path = capture_image()
    if saved_path:
        print(f"Success: {saved_path}")
