# ESP32 Setup Guile for running `lights_controller.ino`

## Download Arduino IDE
1. Access and download the Arduino IDE fetup file at [https://www.arduino.cc/en/software/](https://www.arduino.cc/en/software/)
2. Open the `.exe` file and then install it

## Install necessary library and driver
1. Open Arduino IDE.
2. Follow the instructions on [https://randomnerdtutorials.com/installing-the-esp32-board-in-arduino-ide-windows-instructions/](https://randomnerdtutorials.com/installing-the-esp32-board-in-arduino-ide-windows-instructions/)
3. Download the CP210x driver at [https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers?tab=downloads](https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers?tab=downloads)

## Install necessary libraries in Arduino IDE
Go to `Library Manager` on the toolbar then install these libraries:
- `PubSubClient` by Nick O’Leary
- `ArduinoJson` by Benoît Blanchon

## Open the code and compile
1. Go to `Tools`:
   - Select the right `Port` (ex: COM4, COM5,...)
   - Select the Board `DOIT ESP32 DEVKIT V1` in `esp32` category
2. Open the `lights_controller.ino` file in Arduino IDE
3. Click `Verify` (check icon) if you want to verify if the code is working fine (optional)
4. Click `Upload` (right arrow icon) if you want to upload the code to ESP32 for running
5. Go to `Tools` → `Serial Monitor` to see logs of the ESP32