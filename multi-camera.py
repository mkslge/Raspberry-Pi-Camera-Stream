from flask import Flask, Response
import cv2
import threading
import subprocess
import numpy as np
import time

app = Flask(__name__)

#dimensions
WIDTH = 640
HEIGHT = 480

#shared frame buffer
latest_frame = None
lock = threading.Lock()

def camera_capture():
    global latest_frame
    #set up command
    command = [
        "libcamera-vid",
        "-t", "0",
        "--width", str(WIDTH), "--height", str(HEIGHT), "--framerate", "30",
        "--codec", "yuv420",
        "--inline",
        "--output", "-"
    ]
    #make new sub process each time a new user opens web app
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    frame_size = WIDTH * HEIGHT * 3 // 2


    while True:
        #reads output of command
        raw_frame = process.stdout.read(frame_size)
        
        #if its null we stop
        if not raw_frame:
            break

        #turns byte object into int array
        yuv_frame = np.frombuffer(raw_frame, dtype=np.uint8)

        #create array
        yuv = np.zeros((HEIGHT * 3 // 2, WIDTH), dtype=np.uint8)

        #gets size of y plane (duh)
        y_plane_size = WIDTH * HEIGHT

        #transforms array into matrix
        yuv[:HEIGHT, :] = yuv_frame[:y_plane_size].reshape((HEIGHT, WIDTH))

        #gets u_planes end boundary
        u_plane_size = y_plane_size + WIDTH * HEIGHT // 4

        #extract u_plane data, starting at end of y_plane
        u_plane = yuv_frame[y_plane_size : u_plane_size].reshape((HEIGHT // 2, WIDTH // 2))

        #place u_plane into correct part of matrix
        yuv[HEIGHT:HEIGHT + (HEIGHT // 4), :WIDTH // 2] = u_plane[:(HEIGHT // 2) // 2, :]
        yuv[HEIGHT + (HEIGHT // 4):HEIGHT + (HEIGHT // 2), :WIDTH // 2] = u_plane[(HEIGHT // 2) // 2:, :]

        #extract v plane data from yuv frame
        v_plane = yuv_frame[u_plane_size:].reshape((HEIGHT // 2, WIDTH // 2))

        #put v plane into correct part of matrix
        yuv[HEIGHT:HEIGHT + (HEIGHT // 4), WIDTH // 2:] = v_plane[:(HEIGHT // 2) // 2, :]
        yuv[HEIGHT + (HEIGHT // 4):HEIGHT + (HEIGHT // 2), WIDTH // 2:] = v_plane[(HEIGHT // 2) // 2:, :]


        #convert into color and flip the camera so it doesnt look like its always upside down
        frame_bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
        frame_bgr = cv2.flip(frame_bgr, 0)

        #use jpeg format
        _, jpeg = cv2.imencode('.jpg', frame_bgr)


        #make sure we have the lock and then update latest frame :)
        with lock:
            latest_frame = jpeg.tobytes()

        #sleep for certain amount (you can adjust FPS)
        time.sleep(1 / 5)  #~5fps


def generate_frames():

    while True:
        #make sure we have the mutex
        with lock:
            #if its null dont update frame and keep going
            if latest_frame is None:
                continue
            #otherwise update frame
            frame = latest_frame

        #send frame to http client
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

        time.sleep(0.03)  #chill for a bit to avoid hammering clients


#send response to client
@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

#################################### MAIN ##############################
if __name__ == '__main__':
    #start the camera in a background thread
    threading.Thread(target=camera_capture, daemon=True).start()

    #start flask server
    app.run(host='0.0.0.0', port=5000, threaded=True)
    
