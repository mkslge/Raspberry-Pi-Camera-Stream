import numpy as np

app = Flask(__name__)

WIDTH = 640
HEIGHT = 480

def generate_frames():
    command = [
        "libcamera-vid",
        "-t", "0",  #run forever
        "--width", "640", "--height", "480", "--framerate", "30",
        "--codec", "yuv420",  #request YUV420 format
        "--inline",
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

        #reshape the YUV data
        yuv = np.zeros((HEIGHT * 3 // 2, WIDTH), dtype=np.uint8)

	
	#y plane (full resolution)
        yuv[:HEIGHT, :] = yuv_frame[:WIDTH*HEIGHT].reshape((HEIGHT , WIDTH))

        #u plane (quarter resolution, every other row/column)
        u_plane = yuv_frame[WIDTH * HEIGHT:WIDTH * HEIGHT + WIDTH * HEIGHT//4].reshape((HEIGHT // 2, WIDTH // 2))
        yuv[HEIGHT:HEIGHT + (HEIGHT // 4), :WIDTH // 2] = u_plane[:(HEIGHT // 2) // 2, :]
        yuv[HEIGHT + (HEIGHT // 4):HEIGHT + (HEIGHT // 2), :WIDTH // 2] = u_plane[(HEIGHT // 2) // 2:, :]

        #v plane (quarter resolution, every other row/column)
        v_plane = yuv_frame[WIDTH * HEIGHT + WIDTH * HEIGHT // 4:].reshape((HEIGHT // 2, WIDTH // 2))
        yuv[HEIGHT:HEIGHT + (HEIGHT // 4), WIDTH // 2:] = v_plane[:(HEIGHT // 2) // 2, :]
        yuv[HEIGHT + (HEIGHT // 4):HEIGHT + (HEIGHT // 2), WIDTH // 2:] = v_plane[(HEIGHT // 2) // 2:, :]

        #convert YUV to BGR
        frame_bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)

        frame_bgr = cv2.flip(frame_bgr, 0)

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
