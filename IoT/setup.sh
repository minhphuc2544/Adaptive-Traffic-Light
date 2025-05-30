#!/bin/bash

echo "Setting up Raspberry Pi for camera.py..."

# Update system
sudo apt update && sudo apt upgrade -y

# Enable camera (for legacy PiCamera + PiCamera2)
sudo raspi-config nonint do_camera 0

# Install system packages
sudo apt install -y git ffmpeg python3-pip python3-picamera2 python3-picamera python3-libcamera libatlas-base-dev

# Upgrade pip
pip3 install --upgrade pip

# Install Python packages
pip3 install numpy opencv-python-headless

# Set GPU memory (recommended for camera preview/processing)
echo 'gpu_mem=128' | sudo tee -a /boot/config.txt

# Add user to video group (camera access permission)
sudo usermod -a -G video $USER

echo "Setup complete!"
echo "Please reboot your Raspberry Pi now to apply changes:"
echo "sudo reboot"