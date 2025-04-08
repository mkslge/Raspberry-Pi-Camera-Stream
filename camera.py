from flask import Flask, Response
import cv2
import subprocess

app = Flask(__name__)

def generate_frames():
    # Start libcamera-vid in a subprocess
    command = [
        "libcamera-vid",
        "-t", "0",  # Run indefinitely
        "--width", "640", "--height", "480", "--framerate", "30",
        "--inline",  # Stream the video
        "--output", "-"
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    while True:
        # Read each frame from the video stream
        frame = process.stdout.read(1024 * 1024)  # Adjust size if needed
        if not frame:
            break
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/')
def index():
    return "Camera stream is live! Access the stream at /video_feed"

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
