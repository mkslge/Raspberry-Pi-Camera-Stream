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
        "--codec", "yuv420",  # Explicitly request YUV420 format
        "--inline",  # Stream the video
        "--output", "-"
    ]
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    frame_size = 640 * 480 * 3 // 2  # YUV420 size
    
    while True:
        # Read raw video data (YUV420 format)
        raw_frame = process.stdout.read(frame_size)
        if not raw_frame:
            break
            
        # Convert the raw frame into a numpy array
        yuv_frame = np.frombuffer(raw_frame, dtype=np.uint8)
        
        # Reshape the YUV data correctly for YV12/I420 format
        # Create a properly formatted YUV frame that OpenCV can convert
        yuv = np.zeros((480 * 3 // 2, 640), dtype=np.uint8)
        
        # Y plane (full resolution)
        yuv[:480, :] = yuv_frame[:640*480].reshape((480, 640))
        
        # U plane (quarter resolution, every other row/column)
        u_plane = yuv_frame[640*480:640*480 + 640*480//4].reshape((240, 320))
        yuv[480:480+120, :640//2] = u_plane[:240//2, :]
        yuv[480+120:480+240, :640//2] = u_plane[240//2:, :]
        
        # V plane (quarter resolution, every other row/column)
        v_plane = yuv_frame[640*480 + 640*480//4:].reshape((240, 320))
        yuv[480:480+120, 640//2:] = v_plane[:240//2, :]
        yuv[480+120:480+240, 640//2:] = v_plane[240//2:, :]
        
        # Convert YUV to BGR using the correct format
        frame_bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
        
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
