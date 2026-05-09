# BarcodeCheck

BarcodeCheck is a Python desktop application for validating QR codes and barcode scans during packaging, product inspection, or inventory workflows. The app uses a Tkinter GUI to compare scanned input against a configured target code and display a clear pass/fail result.

## Features

- Load a list of valid target codes from a `.txt` or `.csv` file
- Support for standard keyboard scanner input
- Support for camera-based QR code scanning via OpenCV
- Support for serial scanner input through COM/serial ports
- Visual pass/fail feedback with status messages and background color changes
- Sound alerts for matches and mismatches
- Lockable settings with PIN protection

## Requirements

- Python 3.10+
- `opencv_contrib_python`
- `opencv_python`
- `Pillow`
- `pyserial`
- `pyzbar`

> Note: The current implementation uses `winsound`, which is available on Windows. For full cross-platform compatibility, replace or conditionally handle the sound logic.

## Installation

1. Create and activate a Python virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:

   ```bash
   python main.py
   ```

## Usage

1. Start the app and set the target code by typing it directly or loading a text/CSV file.
2. Choose the scanner source:
   - `Standard Mode (Keyboard)` for keyboard-based barcode scanners
   - `Camera 0`, `Camera 1`, etc. for webcam QR scanning
   - A serial port entry for COM/serial scanner devices
3. Scan a code. The app compares the scanned value with the target code.
4. Successful matches show a green indicator and a beep.
5. Mismatches show a red warning and an alert tone.
6. Use `SAVE (LOCK)` to lock the settings, then unlock with the PIN code `2025`.

## Example Data

The repository includes `codes.txt` with example codes such as:

- `PRD-001`
- `PRD-002`
- `PRD-003`
- `TEST-CODE`
- `ABC-XYZ-123`
- `SPXVN05846065320B`

## Notes

- The app is designed for quick barcode validation in packaging or inspection operations.
- Camera scanning is handled by OpenCV and can display a live preview when a webcam is selected.
- Serial mode listens for incoming barcode data from connected serial ports.
- If you need cross-platform sound support, replace `winsound.Beep` with a platform-independent audio library.

