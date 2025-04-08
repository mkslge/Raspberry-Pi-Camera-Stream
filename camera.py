from flask import Flask, Response
import cv2
import subprocess
import numpy as np

app = Flask(__name__)

WIDTH = 640
HEIGHT =  480

def generate_frames():
    command = [
        "libcamera-vid",
        "-t", "0",  #run forever
        "--width", "640", "--height", "480", "--framerate", "30",
        "--codec", "yuv420",  # Explicitly request YUV420 format
        "--inline",  # Stream the video
        "--output", "-"
    ]
    #start libcamera
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    frame_size = WIDTH * HEIGHT * 3 // 2  #yuv420 format
    
    while True:
        #read video data
        raw_frame = process.stdout.read(frame_size)
	#null check
        if not raw_frame:
            break
            
        #convert raw frame into a numpy array
        yuv_frame = np.frombuffer(raw_frame, dtype=np.uint8)
        
        #reshape the YUV data correctly for YV12/I420 format
        yuv = np.zeros((HEIGHT * 3 // 2, WIDTH), dtype=np.uint8)
        
        #y plane (full resolution)
        yuv[:480, :] = yuv_frame[:640*480].reshape((480, 640))
        
        #u plane (quarter resolution, every other row/column)
        u_plane = yuv_frame[640*480:640*480 + 640*480//4].reshape((240, 320))
        yuv[480:480+120, :640//2] = u_plane[:240//2, :]
        yuv[480+120:480+240, :640//2] = u_plane[240//2:, :]
        
        #v plane (quarter resolution, every other row/column)
        v_plane = yuv_frame[640*480 + 640*480//4:].reshape((240, 320))
        yuv[480:480+120, 640//2:] = v_plane[:240//2, :]
        yuv[480+120:480+240, 640//2:] = v_plane[240//2:, :]
        
        #convert YUV to BGR using the correct format
        frame_bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
        
        #encode the frame as jpg
        _, jpeg_frame = cv2.imencode('.jpg', frame_bgr)
        
        #yield the frame
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg_frame.tobytes() + b'\r\n\r\n')

@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
