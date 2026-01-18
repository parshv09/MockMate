import cv2
import numpy as np
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5
)

def analyze_eye_contact_and_head(image_bytes):
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        return {"eye_contact": False, "head_movement": False}

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(rgb)

    if not result.multi_face_landmarks:
        return {"eye_contact": False, "head_movement": False}

    landmarks = result.multi_face_landmarks[0].landmark

    nose = landmarks[1]  # nose tip
    eye_contact = 0.4 < nose.x < 0.6
    head_movement = not eye_contact

    return {
        "eye_contact": eye_contact,
        "head_movement": head_movement
    }
