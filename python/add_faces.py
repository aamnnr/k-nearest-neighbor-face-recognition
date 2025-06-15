import cv2
import pickle
import numpy as np
import os
import sys

# Inisialisasi kamera video
video = cv2.VideoCapture(1)
if not video.isOpened():
    print("Error: Tidak dapat membuka kamera. Pastikan kamera terhubung dan tidak digunakan oleh aplikasi lain.")
    sys.exit(1)

# Menentukan jalur direktori dasar tempat skrip ini berada
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Direktori untuk menyimpan file model dan cascade
DATA_DIR = os.path.join(BASE_DIR, 'data')
# Direktori utama untuk menyimpan hasil capture foto wajah
CAPTURES_ROOT_DIR = os.path.join(BASE_DIR, 'captured_faces')

# Memastikan direktori 'data' dan 'captured_faces' ada
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CAPTURES_ROOT_DIR, exist_ok=True)

# Memuat model deteksi wajah Haar Cascade
facedetect = cv2.CascadeClassifier(os.path.join(DATA_DIR, 'haarcascade_frontalface_default.xml'))
if facedetect.empty():
    print("Error: haarcascade_frontalface_default.xml tidak ditemukan atau tidak dapat dimuat. Pastikan file ada di folder 'data'.")
    video.release()
    sys.exit(1)

faces_data = [] # List untuk menyimpan data wajah yang akan dilatih
total_capture = 100 # Jumlah total gambar wajah yang akan diambil

# Mengambil face_id dan user_name dari argumen baris perintah
if len(sys.argv) > 2:
    face_id = sys.argv[1]
    user_name_raw = sys.argv[2]
    # Membersihkan user_name agar aman untuk nama folder (misal: ganti spasi dengan underscore)
    user_name_clean = "".join(c for c in user_name_raw if c.isalnum() or c.isspace()).strip()
    user_name_folder = user_name_clean.replace(" ", "_")
else:
    print("Error: face_id dan user_name tidak diberikan sebagai argumen. Penggunaan: python add_faces.py <face_id> <user_name>")
    video.release()
    cv2.destroyAllWindows()
    sys.exit(1)

# Direktori khusus untuk menyimpan capture foto wajah pengguna ini dengan format (nama)_(face_id)
USER_CAPTURE_DIR = os.path.join(CAPTURES_ROOT_DIR, f"{user_name_folder}_{face_id}")
os.makedirs(USER_CAPTURE_DIR, exist_ok=True) # Buat folder khusus untuk user ini

print(f"Mulai penangkapan wajah untuk Face ID: {face_id} (Nama: {user_name_raw})")
print(f"Gambar akan disimpan di: {USER_CAPTURE_DIR}")

# Loop utama untuk menangkap frame dari kamera
while True:
    ret, frame = video.read()
    if not ret:
        print("Gagal mengambil frame. Keluar.")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # Mengubah frame ke skala abu-abu
    # Mendeteksi wajah dalam frame
    faces = facedetect.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        # Memotong area wajah dari frame
        crop_img = frame[y:y+h, x:x+w, :]
        # Mengubah ukuran gambar wajah menjadi 128x128 piksel
        resized_img = cv2.resize(crop_img, (128, 128))

        # Jika jumlah capture belum mencapai target, simpan gambar dan tambahkan ke data
        if len(faces_data) < total_capture:
            # Menyimpan gambar yang di-resize ke folder khusus user
            img_filename = os.path.join(USER_CAPTURE_DIR, f"{len(faces_data) + 1:03d}.jpg")
            cv2.imwrite(img_filename, resized_img)

            faces_data.append(resized_img) # Menambahkan gambar ke list data untuk .pkl

        # Menampilkan status penangkapan di frame
        cv2.putText(frame, f"Capturing: {len(faces_data)}/{total_capture}", (50, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 255), 1)
        # Menggambar persegi panjang di sekitar wajah yang terdeteksi
        cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 50, 255), 1)

    # Menampilkan frame
    cv2.imshow("Frame", frame)
    k = cv2.waitKey(1) # Menunggu 1 milidetik untuk input keyboard
    # Menghentikan loop jika tombol 'q' ditekan atau jumlah capture mencapai target
    if k == ord('q') or len(faces_data) == total_capture:
        break

# Melepaskan sumber daya kamera
video.release()
# Menutup semua jendela OpenCV
cv2.destroyAllWindows()

# Memeriksa jika tidak ada wajah yang ditangkap
if len(faces_data) == 0:
    print("Tidak ada wajah yang ditangkap. Pembatalan penyimpanan ke file PKL.")
    sys.exit(1)

# Mengubah list data wajah menjadi array NumPy
faces_data = np.asarray(faces_data)
# Mengubah bentuk array menjadi 2D (jumlah sampel x fitur)
faces_data = faces_data.reshape(len(faces_data), -1)

names_pkl_path = os.path.join(DATA_DIR, 'names.pkl')
faces_pkl_path = os.path.join(DATA_DIR, 'faces.pkl')

# Memproses dan menyimpan label (face_id) ke names.pkl
if not os.path.exists(names_pkl_path):
    # Jika names.pkl belum ada, buat baru dengan face_id yang baru
    names = [face_id] * len(faces_data)
    with open(names_pkl_path, 'wb') as f:
        pickle.dump(names, f)
else:
    # Jika names.pkl sudah ada, muat, tambahkan face_id yang baru, lalu simpan kembali
    with open(names_pkl_path, 'rb') as f:
        names = pickle.load(f)
    names = names + [face_id] * len(faces_data)
    with open(names_pkl_path, 'wb') as f:
        pickle.dump(names, f)

# Memproses dan menyimpan data wajah ke faces.pkl
if not os.path.exists(faces_pkl_path):
    # Jika faces.pkl belum ada, buat baru dengan data wajah yang baru
    with open(faces_pkl_path, 'wb') as f:
        pickle.dump(faces_data, f)
else:
    # Jika faces.pkl sudah ada, muat, tambahkan data wajah yang baru, lalu simpan kembali
    with open(faces_pkl_path, 'rb') as f:
        faces = pickle.load(f)
    faces = np.append(faces, faces_data, axis=0) # Menggabungkan data wajah yang sudah ada dengan yang baru
    with open(faces_pkl_path, 'wb') as f:
        pickle.dump(faces, f)

print(f"Pendaftaran wajah untuk Face ID {face_id} berhasil disimpan di PKL files dan {len(faces_data)} gambar disimpan di {USER_CAPTURE_DIR}.")
