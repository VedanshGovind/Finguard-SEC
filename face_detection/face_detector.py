import cv2
import numpy as np
from typing import List
from app.config import settings

def detect_faces(frames: List[np.ndarray]) -> List[np.ndarray]:
    """
    Detects faces and adds padding to include hair/ears.
    """
    
    # PARAMETER: How much to expand the tight face box
    # 0.0 = Tight crop (chin to eyebrows)
    # 0.5 = 50% expansion (includes hair, ears, neck)
    PADDING_FACTOR = 0.5 
    
    if len(frames) == 0:
        return []
    
    # Load Haar Cascade
    try:
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        if face_cascade.empty():
            print("[FACE_DETECT] Failed to load Haar Cascade")
            return []
    except Exception as e:
        print(f"[FACE_DETECT] Error loading cascade: {e}")
        return []
    
    detected_faces = []
    
    for idx, frame in enumerate(frames):
        try:
            height, width = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            for (x, y, w, h) in faces:
                # --- PADDING LOGIC START ---
                # Calculate padding amount based on face size
                pad_w = int(w * PADDING_FACTOR)
                pad_h = int(h * PADDING_FACTOR)
                
                # Apply padding to coordinates (center the expansion)
                x_new = max(0, x - pad_w // 2)
                y_new = max(0, y - pad_h // 2)
                w_new = min(width - x_new, w + pad_w)
                h_new = min(height - y_new, h + pad_h)
                # --- PADDING LOGIC END ---

                # Extract padded face
                face_crop = frame[y_new:y_new+h_new, x_new:x_new+w_new]
                
                if face_crop.size == 0:
                    continue
                
                # Resize to Model Input Size (299x299 for Xception)
                try:
                    face_resized = cv2.resize(
                        face_crop, 
                        (settings.FACE_IMAGE_SIZE, settings.FACE_IMAGE_SIZE),
                        interpolation=cv2.INTER_AREA
                    )
                    
                    # Normalization [0, 1]
                    face_normalized = face_resized.astype(np.float32) / 255.0
                    detected_faces.append(face_normalized)
                except Exception as e:
                    continue
                
        except Exception:
            continue
    
    print(f"[FACE_DETECT] Total faces detected: {len(detected_faces)}")
    return detected_faces


# ---------------------------------------------------------------------------
# Live-verification detector
# ---------------------------------------------------------------------------
_CASCADE = None


def _get_cascade():
    global _CASCADE
    if _CASCADE is None:
        _CASCADE = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
    return _CASCADE


def detect_primary_faces(frames: List[np.ndarray]) -> List[np.ndarray]:
    """
    Webcam-friendly variant of detect_faces(). The crop that reaches the model is
    produced exactly like detect_faces() (same 0.5 padding, size, [0,1] scaling),
    only the *selection* of crops differs:

    - detection runs on a downscaled, histogram-equalised copy (several times faster
      and more reliable under poor webcam lighting)
    - only the LARGEST face per frame is kept (the person in front of the camera),
      so background false positives no longer pollute the video score
    - minimum face size is relative to the frame, which rejects tiny false hits
    - frames with no hit get one relaxed retry before being skipped

    Args:
        frames: RGB uint8 frames (output of normalize_frames)
    """
    PADDING_FACTOR = 0.5
    cascade = _get_cascade()
    if cascade.empty() or len(frames) == 0:
        return []

    out = []
    for frame in frames:
        try:
            height, width = frame.shape[:2]
            scale = min(1.0, settings.LIVE_DETECT_WIDTH / float(width))
            small = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1.0 else frame
            gray = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_RGB2GRAY))
            min_side = int(max(30, 0.12 * min(gray.shape[:2])))

            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                             minSize=(min_side, min_side))
            if len(faces) == 0:
                faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3,
                                                 minSize=(min_side, min_side))
            if len(faces) == 0:
                continue

            x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
            x, y, w, h = int(x / scale), int(y / scale), int(w / scale), int(h / scale)

            pad_w, pad_h = int(w * PADDING_FACTOR), int(h * PADDING_FACTOR)
            x_new, y_new = max(0, x - pad_w // 2), max(0, y - pad_h // 2)
            w_new, h_new = min(width - x_new, w + pad_w), min(height - y_new, h + pad_h)

            crop = frame[y_new:y_new + h_new, x_new:x_new + w_new]
            if crop.size == 0:
                continue
            crop = cv2.resize(crop, (settings.FACE_IMAGE_SIZE, settings.FACE_IMAGE_SIZE),
                              interpolation=cv2.INTER_AREA)
            out.append(crop.astype(np.float32) / 255.0)
        except Exception:
            continue
    return out