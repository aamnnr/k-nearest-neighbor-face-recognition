from sklearn.neighbors import KNeighborsClassifier, NearestNeighbors
import cv2
import pickle
import numpy as np
import os
import sys
import time  # Import modul time untuk mengukur delay
import requests
import json

video = cv2.VideoCapture(1)
if not video.isOpened():
    print("Error: Tidak dapat membuka aliran video.")
    sys.exit(1)

# Dapatkan direktori dasar tempat skrip ini berada
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')  # Path ke folder 'data'

# Pastikan folder data ada
os.makedirs(DATA_DIR, exist_ok=True)

# Gunakan path absolut untuk file Haar Cascade
facedetect = cv2.CascadeClassifier(os.path.join(DATA_DIR, 'haarcascade_frontalface_default.xml'))

# Periksa apakah classifier berhasil dimuat
if facedetect.empty():
    print(f"Error: haarcascade_frontalface_default.xml tidak ditemukan atau tidak dapat dimuat dari {os.path.join(DATA_DIR, 'haarcascade_frontalface_default.xml')}.")
    video.release()
    cv2.destroyAllWindows()
    sys.exit(1)

# Gunakan path absolut untuk file pickle
try:
    names_pkl_path = os.path.join(DATA_DIR, 'names.pkl')
    faces_pkl_path = os.path.join(DATA_DIR, 'faces.pkl')

    with open(names_pkl_path, 'rb') as w:
        LABELS = pickle.load(w)  # Sekarang LABELS berisi face_id
    with open(faces_pkl_path, 'rb') as f:
        FACES = pickle.load(f)
    print(f"Berhasil memuat {len(LABELS)} label dan {len(FACES)} wajah dari file PKL.")
except FileNotFoundError:
    print(f"Error: 'names.pkl' atau 'faces.pkl' tidak ditemukan di {DATA_DIR}. Harap jalankan add_faces.py terlebih dahulu.")
    video.release()
    cv2.destroyAllWindows()
    sys.exit(1)
except EOFError:
    print(f"Error: 'names.pkl' atau 'faces.pkl' kosong di {DATA_DIR}. Harap jalankan add_faces.py lagi.")
    video.release()
    cv2.destroyAllWindows()
    sys.exit(1)

# Pastikan FACES tidak kosong sebelum melatih KNN dan Similarity
if len(FACES) == 0:
    print("Error: Tidak ada data wajah ditemukan di faces.pkl. Harap tambahkan wajah sebelum menjalankan program ini.")
    video.release()
    cv2.destroyAllWindows()
    sys.exit(1)

knn = KNeighborsClassifier(n_neighbors=3)
knn.fit(FACES, LABELS)  # LABELS sekarang adalah face_id
print("KNN classifier berhasil dilatih.")

similarity = NearestNeighbors(n_neighbors=30,
                             metric='cosine',
                             algorithm='brute',
                             n_jobs=-1)
similarity.fit(FACES)
print("Model kemiripan NearestNeighbors berhasil dilatih.")

# Fungsi untuk mendapatkan nama pengguna dari face_id melalui API PHP
def get_user_name_from_face_id(face_id):
    url = 'http://localhost/presensi_wajah/php/get_user_by_face_id.php'
    try:
        response = requests.get(url, params={'face_id': face_id})
        response.raise_for_status()  # Akan memunculkan HTTPError untuk status kode 4xx/5xx
        user_data = response.json()
        if user_data and 'error' not in user_data:
            return user_data.get('nama', f"Pengguna ID {face_id}")
        print(f"Detail pengguna untuk face_id {face_id}: {user_data}")
        return f"Pengguna ID {face_id}"
    except requests.exceptions.RequestException as e:
        print(f"Error mengambil detail pengguna untuk face_id {face_id}: {e}")
        return f"Pengguna ID {face_id}"
    except json.JSONDecodeError:
        print(f"Error mendekode JSON untuk face_id {face_id}. Respons: {response.text}")
        return f"Pengguna ID {face_id}"

print("Memulai putaran uji coba pengenalan wajah...")
while True:
    ret, frame = video.read()
    if not ret:
        print("Gagal mengambil frame. Keluar dari putaran.")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = facedetect.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=8, minSize=(50, 50), flags=cv2.CASCADE_SCALE_IMAGE)
    
    for (x, y, w, h) in faces:
        # --- Mulai pengukuran waktu untuk proses pengenalan ---
        start_recognition_time = time.time() 

        crop_img = frame[y:y + h, x:x + w, :]
        resized_img = cv2.resize(crop_img, (128, 128), interpolation=cv2.INTER_AREA).flatten().reshape(1, -1)
        
        predicted_face_id = knn.predict(resized_img)[0]
        
        distances, _ = similarity.kneighbors(resized_img, n_neighbors=1, return_distance=True)
        nbrs_distance = distances[0][0]
        
        SIMILARITY_THRESHOLD = 0.1
        
        display_text = "Tidak Dikenal"
        box_color = (0, 0, 255)  # Merah
        text_color = (255, 255, 255)  # Putih
        
        if predicted_face_id in LABELS and nbrs_distance < SIMILARITY_THRESHOLD:
            nama_pengguna = get_user_name_from_face_id(predicted_face_id)
            display_text = f"Dikenal: {nama_pengguna}"
            box_color = (0, 255, 0)  # Hijau
        else:
            nama_pengguna = "Tidak Dikenal"
            display_text = "Tidak Dikenal"
            box_color = (0, 0, 255)  # Merah

        # --- Selesai pengukuran waktu dan hitung delay ---
        end_recognition_time = time.time()
        recognition_delay = end_recognition_time - start_recognition_time
        
        # Tambahkan informasi delay ke display text
        display_text_with_delay = f"{display_text} ({recognition_delay:.2f}s)"
        
        # Cetak ke konsol
        print(f"Waktu {display_text_with_delay} (ID: {predicted_face_id}, Jarak: {nbrs_distance:.4f})")

        # --- Bagian Penggambaran Kotak dan Teks ---
        cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)

        (text_width, text_height), baseline = cv2.getTextSize(display_text_with_delay, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        
        bg_x1 = x
        bg_y1 = y - text_height - baseline - 10
        bg_x2 = x + text_width + 10
        bg_y2 = y - 5

        bg_y1 = max(0, bg_y1)
        bg_y2 = max(0, bg_y2)
        bg_x1 = max(0, bg_x1)
        bg_x2 = max(0, bg_x2)

        cv2.rectangle(frame, (bg_x1, bg_y1), (bg_x2, bg_y2), box_color, -1)
        cv2.putText(frame, display_text_with_delay, (x + 5, y - baseline - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 1, cv2.LINE_AA)
        # --- Akhir Bagian Penggambaran ---

    # Tampilkan frame tanpa background
    cv2.imshow("Uji Coba Pengenalan Wajah", frame)
    
    k = cv2.waitKey(1)
    if k == ord('q'):
        print("Tombol 'q' ditekan. Keluar.")
        break

video.release()
cv2.destroyAllWindows()
print("Program dihentikan.")
