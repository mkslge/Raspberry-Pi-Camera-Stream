# Live Video Streaming with Flask and libcamera

This project sets up a simple live video streaming server using Flask. It captures video from a Raspberry Pi camera using `libcamera-vid`, and streams it to your local network



## Reqs
- A Raspberry Pi with a camera module connected.
- Python 3.x installed.
- Required Python libraries:
  - Flask
  - OpenCV (cv2)
  - Numpy

You can install the dependencies by running:
```bash
pip install flask opencv-python numpy
```

To run the program:
```bash
python camera.py
```
To run the multstream program:
```bash
python multi-camera.py
```
