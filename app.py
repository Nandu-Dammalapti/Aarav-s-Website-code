import os
import cv2
import mediapipe as mp
import numpy as np
import base64
import uuid
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PROCESSED_FOLDER'] = 'static/processed'

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# MediaPipe setup
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def calculate_angle(a, b, c):
    """
    Calculates angle at point b (in degrees)
    a, b, c are [x, y] coordinates
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    ba = a - b
    bc = c - b

    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    angle = np.degrees(np.arccos(cosine_angle))

    return angle


def process_video(video_path):
    """
    Process video and extract frames with pose detection
    Returns list of processed frames and angle data
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        return None, "Error: Could not open video file."

    frames_data = []
    frame_count = 0
    skip_frames = 5  # Process every 5th frame for performance

    with mp_pose.Pose(min_detection_confidence=0.5,
                      min_tracking_confidence=0.5) as pose:

        while cap.isOpened():
            ret, frame = cap.read()

            if not ret:
                break

            frame_count += 1

            # Skip frames for performance
            if frame_count % skip_frames != 0:
                continue

            # Resize frame for better performance
            height, width = frame.shape[:2]
            if width > 640:
                scale = 640 / width
                frame = cv2.resize(frame, (640, int(height * scale)))

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False

            results = pose.process(image)

            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            frame_info = {
                'frame_number': frame_count,
                'left_angle': None,
                'right_angle': None,
                'bad_form': False,
                'image': None
            }

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark

                # Get required landmarks
                # Left side
                left_shoulder = [landmarks[11].x, landmarks[11].y]
                left_elbow = [landmarks[13].x, landmarks[13].y]
                left_hip = [landmarks[23].x, landmarks[23].y]

                # Right side
                right_shoulder = [landmarks[12].x, landmarks[12].y]
                right_elbow = [landmarks[14].x, landmarks[14].y]
                right_hip = [landmarks[24].x, landmarks[24].y]

                # Compute angles
                left_angle = calculate_angle(left_elbow, left_shoulder, left_hip)
                right_angle = calculate_angle(right_elbow, right_shoulder, right_hip)

                frame_info['left_angle'] = round(left_angle, 2)
                frame_info['right_angle'] = round(right_angle, 2)

                # Check bad form
                bad_form = (left_angle > 30) or (right_angle > 30)
                frame_info['bad_form'] = bad_form

                # Display results on image
                if bad_form:
                    cv2.putText(image,
                                "BAD FORM",
                                (50, 50),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                1.2,
                                (0, 0, 255),
                                3,
                                cv2.LINE_AA)
                else:
                    cv2.putText(image,
                                "GOOD FORM",
                                (50, 50),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                1.2,
                                (0, 255, 0),
                                3,
                                cv2.LINE_AA)

                # Show angle values
                cv2.putText(image, f"Left Shoulder: {int(left_angle)}°", (50, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(image, f"Right Shoulder: {int(right_angle)}°", (50, 140),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

                # Draw landmarks
                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(66, 135, 245), thickness=2, circle_radius=2)
                )

            # Convert image to base64 for web display
            _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 80])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            frame_info['image'] = f"data:image/jpeg;base64,{img_base64}"

            frames_data.append(frame_info)

            # Limit to 50 frames max for performance
            if len(frames_data) >= 50:
                break

    cap.release()
    return frames_data, None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_video():
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400

        file = request.files['video']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: mp4, avi, mov, mkv, webm'}), 400

        # Save uploaded file
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        # Ensure upload directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        file.save(filepath)

        # Process video
        frames_data, error = process_video(filepath)

        # Clean up uploaded file
        try:
            os.remove(filepath)
        except:
            pass

        if error:
            return jsonify({'error': error}), 500

        if not frames_data:
            return jsonify({'error': 'No frames could be processed'}), 500

        # Calculate summary statistics
        total_frames = len(frames_data)
        bad_form_frames = sum(1 for f in frames_data if f['bad_form'])
        good_form_frames = total_frames - bad_form_frames

        avg_left_angle = np.mean([f['left_angle'] for f in frames_data if f['left_angle'] is not None])
        avg_right_angle = np.mean([f['right_angle'] for f in frames_data if f['right_angle'] is not None])

        summary = {
            'total_frames': total_frames,
            'good_form_frames': good_form_frames,
            'bad_form_frames': bad_form_frames,
            'form_score': round((good_form_frames / total_frames) * 100, 1) if total_frames > 0 else 0,
            'avg_left_angle': round(avg_left_angle, 2) if not np.isnan(avg_left_angle) else 0,
            'avg_right_angle': round(avg_right_angle, 2) if not np.isnan(avg_right_angle) else 0
        }

        return jsonify({
            'success': True,
            'frames': frames_data,
            'summary': summary
        })

    except Exception as e:
        print(f"Error processing video: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Processing error: {str(e)}'}), 500


if __name__ == '__main__':
    os.makedirs('static/uploads', exist_ok=True)
    os.makedirs('static/processed', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
