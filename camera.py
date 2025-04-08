from flask import Flask, Response
import cv2
import subprocess
import numpy as np

app = Flask(__name__)

def generate_frames():
    # Start libcamera-vid in a subprocess with raw output
    command = [
        "libcamera-vid",
        "-t", "0",  # Run indefinitely
        "--width", "640", "--height", "480", "--framerate", "30",
        "--inline",  # Stream the video
        "--output", "-"
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    while True:
        # Read raw video data (YUV420P format)
        raw_frame = process.stdout.read(640 * 480 * 3 // 2)  # 640 * 480 * 3/2 bytes for YUV420P
        if not raw_frame:
            break

        # Convert the raw frame into a numpy array
        frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((480 * 3 // 2, 640))  # YUV420P format

        # Convert YUV to BGR (or RGB) using OpenCV
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_YV12)

        # Encode the frame as JPEG
        _, jpeg_frame = cv2.imencode('.jpg', frame_bgr)

        # Yield the frame as a multipart HTTP response
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg_frame.tobytes() + b'\r\n\r\n')

@app.route('/')
def index():
    return "Camera stream is live! Access the stream at /video_feed"

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
