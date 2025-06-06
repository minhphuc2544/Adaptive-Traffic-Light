#!/bin/bash

echo "Setting up Raspberry Pi for camera.py..."

# Update system
sudo apt update && sudo apt upgrade -y # OKAY

# Enable camera (for legacy PiCamera + PiCamera2)
sudo raspi-config nonint do_camera 0 # OKAY

# Install system packages
sudo apt install -y git ffmpeg python3-pip python3-picamera2 python3-libcamera libatlas-base-dev python3-numpy python3-opencv # OKAY

# Set GPU memory (recommended for camera preview/processing)
echo 'gpu_mem=128' | sudo tee -a /boot/config.txt

# Add user to video group (camera access permission)
sudo usermod -a -G video $USER

# Clone the repo
git clone https://github.com/minhphuc2544/Adaptive-Traffic-Light

echo "Setup complete!"
echo "Please reboot your Raspberry Pi now to apply changes:"
echo "sudo reboot"