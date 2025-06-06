Here is your Bash script turned into a well-formatted **Markdown** setup guide:

````markdown
# 📷 Raspberry Pi Setup Guide for `camera.py`

This guide helps you set up a Raspberry Pi to run `camera.py`, including camera access, required packages, and dependencies.

---

## 🛠️ Steps

### 1. Update the System

```bash
sudo apt update && sudo apt upgrade -y
````

### 2. Enable the Camera

```bash
sudo raspi-config nonint do_camera 0
```

### 3. Install Required System Packages

```bash
sudo apt install -y git ffmpeg python3-pip python3-picamera2 python3-libcamera libatlas-base-dev python3-numpy python3-opencv
```

### 4. Set GPU Memory (for camera preview/processing)

```bash
echo 'gpu_mem=128' | sudo tee -a /boot/config.txt
```

### 5. Add User to `video` Group (camera access)

```bash
sudo usermod -a -G video $USER
```

### 6. Clone the Repository

```bash
git clone https://github.com/minhphuc2544/Adaptive-Traffic-Light
```

---

## ✅ Final Step

Please reboot your Raspberry Pi to apply all changes:

```bash
sudo reboot
```

---

**Setup complete!** 🎉 Your Raspberry Pi is now ready to run `camera.py`.

```

Let me know if you'd like this in Vietnamese or as a `README.md` file.
```
