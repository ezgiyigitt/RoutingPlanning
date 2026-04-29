import cv2
import mediapipe as mp
import time

def test_mediapipe():
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Kamera acilamadi.")
        return

    print("Mediapipe baslatildi. 3 saniye boyunca test ediliyor...")
    start_time = time.time()
    while time.time() - start_time < 3:
        success, image = cap.read()
        if not success:
            break

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(image_rgb)
        
        if results.multi_face_landmarks:
            print(f"Yuz tespit edildi! Landmark sayisi: {len(results.multi_face_landmarks[0].landmark)}")
        else:
            print("Yuz tespit edilemedi.")
        time.sleep(0.5)

    cap.release()
    print("Test bitti.")

if __name__ == "__main__":
    test_mediapipe()
