from flask import Flask, Response
import cv2
import threading
import subprocess
import numpy as np
import time

app = Flask(__name__)

WIDTH = 640
HEIGHT = 480

#shared frame buffer
latest_frame = None
lock = threading.Lock()

def camera_capture():
    global latest_frame
    command = [
        "libcamera-vid",
        "-t", "0",
        "--width", str(WIDTH), "--height", str(HEIGHT), "--framerate", "30",
        "--codec", "yuv420",
        "--inline",
        "--output", "-"
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    frame_size = WIDTH * HEIGHT * 3 // 2

    while True:
        raw_frame = process.stdout.read(frame_size)
        if not raw_frame:
            break

        yuv_frame = np.frombuffer(raw_frame, dtype=np.uint8)
        yuv = np.zeros((HEIGHT * 3 // 2, WIDTH), dtype=np.uint8)

        y_plane_size = WIDTH * HEIGHT
        yuv[:HEIGHT, :] = yuv_frame[:y_plane_size].reshape((HEIGHT, WIDTH))

        u_plane_size = y_plane_size + WIDTH * HEIGHT // 4
        u_plane = yuv_frame[y_plane_size : u_plane_size].reshape((HEIGHT // 2, WIDTH // 2))
        yuv[HEIGHT:HEIGHT + (HEIGHT // 4), :WIDTH // 2] = u_plane[:(HEIGHT // 2) // 2, :]
        yuv[HEIGHT + (HEIGHT // 4):HEIGHT + (HEIGHT // 2), :WIDTH // 2] = u_plane[(HEIGHT // 2) // 2:, :]

        v_plane = yuv_frame[u_plane_size:].reshape((HEIGHT // 2, WIDTH // 2))
        yuv[HEIGHT:HEIGHT + (HEIGHT // 4), WIDTH // 2:] = v_plane[:(HEIGHT // 2) // 2, :]
        yuv[HEIGHT + (HEIGHT // 4):HEIGHT + (HEIGHT // 2), WIDTH // 2:] = v_plane[(HEIGHT // 2) // 2:, :]

        frame_bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
        frame_bgr = cv2.flip(frame_bgr, 0)

        _, jpeg = cv2.imencode('.jpg', frame_bgr)

        with lock:
            latest_frame = jpeg.tobytes()

        time.sleep(1 / 30)  # ~30fps

def generate_frames():
    while True:
        with lock:
            if latest_frame is None:
                continue
            frame = latest_frame

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        time.sleep(0.03)  #avoids hammering clients

@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    #starts the camera in a background thread
    threading.Thread(target=camera_capture, daemon=True).start()

    #starts the Flask server
    app.run(host='0.0.0.0', port=5000, threaded=True)
