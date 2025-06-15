from sklearn.neighbors import KNeighborsClassifier, NearestNeighbors
import cv2
import pickle
import numpy as np
import os
import time
from datetime import datetime, timedelta
import requests
import json
import dlib
from numpy.linalg import norm
from playsound import playsound
from gtts import gTTS

# Fungsi untuk mengubah teks menjadi suara dan memainkannya
def speak(str1):
    audio_filename = "audio.mp3"
    audio_indonesia = gTTS(text=str1, lang="id")
    audio_indonesia.save(audio_filename)
    try:
        playsound(audio_filename)
    except Exception as e:
        print(f"Error memainkan suara: {e}")
    finally:
        if os.path.exists(audio_filename):
            try:
                os.remove(audio_filename)
            except OSError as e:
                print(f"Error menghapus file {audio_filename}: {e}")

# Inisialisasi kamera video
video = cv2.VideoCapture(0)
if not video.isOpened():
    print("Error: Tidak dapat membuka aliran video. Pastikan kamera terhubung dan tidak digunakan oleh aplikasi lain.")
    exit()

# Menentukan jalur direktori untuk data model dan cascade
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Memastikan folder 'data' ada
os.makedirs(DATA_DIR, exist_ok=True)

# Memuat model deteksi wajah dan senyum Haar Cascade
facedetect = cv2.CascadeClassifier(os.path.join(DATA_DIR, 'haarcascade_frontalface_default.xml'))
smile_detector = cv2.CascadeClassifier(os.path.join(DATA_DIR, 'haarcascade_smile.xml'))

# Memeriksa apakah classifier berhasil dimuat
if facedetect.empty():
    print(f"Error: haarcascade_frontalface_default.xml tidak ditemukan atau tidak dapat dimuat dari {os.path.join(DATA_DIR, 'haarcascade_frontalface_default.xml')}. Pastikan file ada di folder 'data'.")
    video.release()
    cv2.destroyAllWindows()
    exit()
if smile_detector.empty():
    print(f"Error: haarcascade_smile.xml tidak ditemukan atau tidak dapat dimuat dari {os.path.join(DATA_DIR, 'haarcascade_smile.xml')}. Pastikan file ada di folder 'data'.")
    video.release()
    cv2.destroyAllWindows()
    exit()

# Memuat data wajah dan label (face_id) dari file pickle
try:
    names_pkl_path = os.path.join(DATA_DIR, 'names.pkl')
    faces_pkl_path = os.path.join(DATA_DIR, 'faces.pkl')

    with open(names_pkl_path, 'rb') as w:
        LABELS = pickle.load(w) # LABELS sekarang berisi face_id
    with open(faces_pkl_path, 'rb') as f:
        FACES = pickle.load(f)
    print(f"Berhasil memuat {len(LABELS)} label dan {len(FACES)} wajah dari file PKL.")
except FileNotFoundError:
    print(f"Error: 'names.pkl' atau 'faces.pkl' tidak ditemukan di {DATA_DIR}. Harap jalankan add_faces.py terlebih dahulu untuk mendaftarkan wajah.")
    video.release()
    cv2.destroyAllWindows()
    exit()
except EOFError:
    print(f"Error: 'names.pkl' atau 'faces.pkl' kosong di {DATA_DIR}. Harap jalankan add_faces.py lagi untuk memastikan data wajah tersimpan.")
    video.release()
    cv2.destroyAllWindows()
    exit()

# Memastikan data wajah tidak kosong sebelum melatih model
if len(FACES) == 0:
    print("Error: Tidak ada data wajah ditemukan di faces.pkl. Harap tambahkan wajah sebelum menjalankan test.py.")
    video.release()
    cv2.destroyAllWindows()
    exit()

# Melatih model K-Nearest Neighbors (KNN) untuk klasifikasi wajah
knn = KNeighborsClassifier(n_neighbors=3)
knn.fit(FACES, LABELS)
print("KNN classifier berhasil dilatih.")

# Melatih model NearestNeighbors untuk mengukur kemiripan wajah (jarak)
similarity = NearestNeighbors(n_neighbors=30,
                              metric='cosine',
                              algorithm='brute',
                              n_jobs=-1)
similarity.fit(FACES)
print("Model kemiripan NearestNeighbors berhasil dilatih.")

# Memuat gambar latar belakang
imgBackground = cv2.imread(os.path.join(BASE_DIR, 'background.png'))
if imgBackground is None:
    print(f"Error: background.png tidak ditemukan atau tidak dapat dimuat dari {os.path.join(BASE_DIR, 'background.png')}.")
    exit()

nama_pengabsen = '' # Variabel untuk menyimpan nama pengabsen yang dikenali

# Parameter untuk deteksi kedipan mata dan senyum
threshold = 0.2
eye_closed = False
kedip = 'X'
color_kedip = (0,0,255) # Merah untuk 'Belum Berhasil'
senyum = 'X'
color_senyum = (0,0,255) # Merah untuk 'Belum Berhasil'

# Memuat model Dlib untuk deteksi landmark wajah
detector = dlib.get_frontal_face_detector()
predictor_path = os.path.join(DATA_DIR, 'shape_predictor_68_face_landmarks.dat')
if not os.path.exists(predictor_path):
    print(f"Error: shape_predictor_68_face_landmarks.dat tidak ditemukan di {predictor_path}. Pastikan file ini ada di folder 'data'.")
    exit()
predictor = dlib.shape_predictor(predictor_path)
print("Dlib face detector dan predictor dimuat.")

def mid_line_distance(p1 ,p2, p3, p4):
    """
    Menghitung jarak Euclidean antara titik tengah dua set poin.
    Digunakan untuk menghitung rasio aspek mata (EAR).

    Args:
        p1 (tuple): Koordinat (x,y) titik pertama.
        p2 (tuple): Koordinat (x,y) titik kedua.
        p3 (tuple): Koordinat (x,y) titik ketiga.
        p4 (tuple): Koordinat (x,y) titik keempat.

    Returns:
        float: Jarak Euclidean antara titik tengah (p1,p2) dan (p3,p4).
    """
    p5 = np.array([int((p1[0] + p2[0])/2), int((p1[1] + p2[1])/2)])
    p6 = np.array([int((p3[0] + p4[0])/2), int((p3[1] + p4[1])/2)])
    return norm(p5 - p6)

def aspect_ratio(landmarks, eye_range):
    """
    Menghitung Eye Aspect Ratio (EAR) untuk mata.
    EAR adalah metrik untuk menentukan apakah mata tertutup atau terbuka.

    Args:
        landmarks (dlib.full_object_detection): Objek yang berisi 68 landmark wajah.
        eye_range (range): Rentang indeks landmark yang sesuai dengan mata tertentu (misal: 36-41 untuk mata kanan).

    Returns:
        float: Nilai Eye Aspect Ratio (EAR).
    """
    eye = np.array(
        [np.array([landmarks.part(i).x, landmarks.part(i).y])
         for i in eye_range]
        )
    # Hitung jarak Euclidean horizontal dan vertikal
    B = norm(eye[0] - eye[3]) # Jarak horizontal antara sudut mata
    A = mid_line_distance(eye[1], eye[2], eye[5], eye[4]) # Jarak vertikal antara kelopak mata
    # Hitung rasio aspek mata
    ear = A / B
    return ear

# Waktu masuk dan pulang yang ditentukan untuk presensi
JAM_MASUK = datetime.strptime("22:15:00", "%H:%M:%S").time()
JAM_PULANG = datetime.strptime("23:00:00", "%H:%M:%S").time()
TOLERANSI_TERLAMBAT = timedelta(minutes=15)

# Cache untuk status absen hari ini di sesi Python
absen_hari_ini = {}

# Mengambil detail pengguna (user_id, nama) dari database PHP berdasarkan face_id yang dikenali.
def get_user_details_from_face_id(face_id):
    url = 'http://localhost/presensi_wajah/php/get_user_by_face_id.php'
    try:
        response = requests.get(url, params={'face_id': face_id})
        response.raise_for_status()
        user_data = response.json()
        if user_data and 'error' not in user_data:
            return user_data 
        print(f"Detail pengguna untuk face_id {face_id}: {user_data}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error mengambil detail pengguna untuk face_id {face_id}: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Error mendekode JSON untuk face_id {face_id}. Respons: {response.text}")
        return None

# Mengambil status presensi (masuk/pulang) pengguna
def get_attendance_status_from_db(user_id, date_for_db):
    url = 'http://localhost/presensi_wajah/php/getData.php'
    params = {'user_id': user_id, 'tanggal': date_for_db}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            if len(data) > 0:
                record = data[0]
                if isinstance(record, dict) and record.get('error'):
                    print(f"Error dalam status kehadiran untuk user {user_id}: {record.get('error')}")
                    return {'masuk': False, 'pulang': False, 'waktu_masuk': None}

                return {
                    'masuk': record.get('waktu_masuk') is not None and record.get('waktu_masuk') != '',
                    'pulang': record.get('waktu_pulang') is not None and record.get('waktu_pulang') != '',
                    'waktu_masuk': record.get('waktu_masuk')
                }
            else: # List kosong, artinya tidak ada catatan kehadiran untuk hari ini
                return {'masuk': False, 'pulang': False, 'waktu_masuk': None}
        elif isinstance(data, dict) and data.get('error'): # Tangani jika PHP mengembalikan dictionary dengan error langsung
            print(f"Error dalam status kehadiran untuk user {user_id}: {data.get('error')}")
            return {'masuk': False, 'pulang': False, 'waktu_masuk': None}

        print(f"Format data tak terduga dari getData.php untuk user {user_id}: {data}")
        return {'masuk': False, 'pulang': False, 'waktu_masuk': None}

    except requests.exceptions.RequestException as e:
        print(f"Error mengambil status kehadiran dari DB untuk user {user_id}: {e}")
        return {'masuk': False, 'pulang': False, 'waktu_masuk': None}
    except json.JSONDecodeError:
        print(f"Error mendekode JSON untuk status kehadiran. Respons: {response.text}")
        return {'masuk': False, 'pulang': False, 'waktu_masuk': None}

print("Memulai putaran pengambilan video...")
while True:
    ret, frame = video.read()
    if not ret:
        print("Gagal mengambil frame. Keluar dari putaran.")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Mendeteksi wajah menggunakan Haar Cascade
    faces = facedetect.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=8, minSize=(50, 50), flags=cv2.CASCADE_SCALE_IMAGE)

    rects = detector(gray, 0) # Mendeteksi wajah menggunakan Dlib untuk landmark

    for rect in rects: # Memproses setiap wajah yang terdeteksi oleh Dlib untuk deteksi kedipan mata
        landmarks = predictor(gray, rect)

        # Menghitung Eye Aspect Ratio (EAR) untuk mata kiri dan kanan
        left_aspect_ratio = aspect_ratio(landmarks, range(42, 48))
        right_aspect_ratio = aspect_ratio(landmarks, range(36, 42))
        ear = (left_aspect_ratio + right_aspect_ratio) / 2.0

        # Logika deteksi kedipan mata
        if ear < threshold:
            eye_closed = True
        elif ear >= threshold and eye_closed:
            kedip = 'Berhasil'
            color_kedip = (0,255,0) # Hijau untuk 'Berhasil'
            eye_closed = False

        # Menampilkan status kedipan mata di layar
        cv2.putText(frame, "Pejamkan Mata :", (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, " {}".format(kedip), (200, 60),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_kedip, 2)

    # Mendeteksi senyum menggunakan Haar Cascade
    smile = smile_detector.detectMultiScale(gray,
    scaleFactor= 1.7, minNeighbors=50,
    minSize=(25, 25))

    for (x, y, w, h) in smile: # Memproses setiap senyum yang terdeteksi oleh OpenCV
        if len(smile) > 0:
            senyum = 'Berhasil'
            color_senyum = (0,255,0) # Hijau untuk 'Berhasil'
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 1) # Menggambar kotak di sekitar senyum (opsional)
    # Menampilkan status senyum di layar
    cv2.putText(frame, "Perlihatkan Gigi :", (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, " {}".format(senyum), (200, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_senyum, 2)

    nama_pengabsen_display = '' # Nama yang akan ditampilkan di frame
    user_id_recognized = None    # ID pengguna yang dikenali
    face_id_recognized = ''      # ID wajah yang dikenali (dari model KNN)

    for (x,y,w,h) in faces: # Memproses setiap wajah yang terdeteksi oleh OpenCV untuk pengenalan
        # Memotong dan mengubah ukuran wajah yang terdeteksi untuk input model KNN
        crop_img = frame[y:y+h, x:x+w, :]
        resized_img = cv2.resize(crop_img, (128,128), interpolation=cv2.INTER_AREA).flatten().reshape(1,-1)

        # Memprediksi face_id menggunakan KNN
        predicted_face_id = knn.predict(resized_img)[0]

        # Menghitung jarak kemiripan ke tetangga terdekat
        distances, _ = similarity.kneighbors(resized_img, n_neighbors=3, return_distance=True)
        nbrs_distance = distances[0][0] # Jarak ke tetangga terdekat pertama

        SIMILARITY_THRESHOLD = 0.2 # Ambang batas kemiripan untuk pengenalan wajah
        print(f"Wajah terdeteksi di ({x},{y},{w},{h}). ID Wajah Terprediksi: {predicted_face_id}, Jarak: {nbrs_distance}")

        display_text = "Tidak Dikenal" # Teks default
        box_color = (0,0,255) # Warna default (Merah untuk Tidak Dikenal)
        text_color = (255,255,255) # Teks putih

        # Logika pengenalan wajah
        if predicted_face_id in LABELS and nbrs_distance < SIMILARITY_THRESHOLD:
            face_id_recognized = predicted_face_id
            user_details = get_user_details_from_face_id(face_id_recognized)

            if user_details:
                user_id_recognized = user_details['user_id']
                nama_pengabsen_display = user_details['nama']
                display_text = nama_pengabsen_display
                box_color = (0,255,0) # Hijau untuk Dikenali
                print(f"Dikenali: {nama_pengabsen_display} (User ID: {user_id_recognized}) - Jarak: {nbrs_distance}")
            else:
                nama_pengabsen_display = "UNKNOWN (Data Pengguna Hilang)"
                display_text = "Tidak Dikenal (Data Pengguna Hilang)"
                face_id_recognized = '' # Reset jika data pengguna tidak ditemukan
                print(f"ID Wajah {predicted_face_id} dikenali, tetapi data pengguna tidak ditemukan di DB. Jarak: {nbrs_distance}")
        else:
            nama_pengabsen_display = "UNKNOWN"
            display_text = "Tidak Dikenal"
            face_id_recognized = ''
            print(f"Wajah tidak dikenali (Jarak {nbrs_distance} >= Threshold {SIMILARITY_THRESHOLD} atau ID tidak ada di LABELS).")

        # Menggambar kotak di sekitar wajah dan menampilkan nama/status
        cv2.rectangle(frame, (x,y), (x+w, y+h), box_color, 2)
        (text_width, text_height), baseline = cv2.getTextSize(display_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)

        # Menghitung posisi latar belakang teks
        bg_x1 = x
        bg_y1 = y - text_height - baseline - 10
        bg_x2 = x + text_width + 10
        bg_y2 = y - 5

        # Membatasi koordinat agar berada di dalam batas frame
        bg_y1 = max(0, bg_y1)
        bg_y2 = max(0, bg_y2)
        bg_x1 = max(0, bg_x1)
        bg_x2 = max(0, bg_x2)

        # Menggambar latar belakang teks dan teks itu sendiri
        cv2.rectangle(frame, (bg_x1, bg_y1), (bg_x2, bg_y2), box_color, -1)
        cv2.putText(frame, display_text, (x + 5, y - baseline - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 1, cv2.LINE_AA)

    # Menyatukan frame kamera dengan gambar latar belakang
    imgBackground[140:140 + frame.shape[0], 40:40 + frame.shape[1]] = frame
    cv2.imshow("SISTEM PRESENSI FACE RECOGNITION", imgBackground)

    k = cv2.waitKey(1)

    # Logika presensi saat kedipan mata dan senyuman terdeteksi
    if kedip == 'Berhasil' and senyum == 'Berhasil':
        print(f"Kedipan dan Senyuman terdeteksi untuk {nama_pengabsen_display}.")
        # Memastikan wajah dikenali DAN data pengguna ditemukan di database
        if nama_pengabsen_display != '' and nama_pengabsen_display != "UNKNOWN" and user_id_recognized is not None:
            status_action = ""
            tipe_absen_to_php = ""
            pesan_speak = ""

            ts = time.time()
            current_datetime = datetime.fromtimestamp(ts)
            date_for_db = current_datetime.strftime("%Y-%m-%d")
            time_for_db = current_datetime.strftime("%H:%M:%S")
            current_time_only = current_datetime.time() # Hanya waktu saat ini

            # Mengambil status absen terbaru dari database PHP
            current_day_data = get_attendance_status_from_db(user_id_recognized, date_for_db)
            is_masuk_recorded = current_day_data['masuk']
            is_pulang_recorded = current_day_data['pulang']
            waktu_masuk_recorded = current_day_data['waktu_masuk']

            print(f"Status absen untuk {nama_pengabsen_display} pada {date_for_db}: Masuk Tercatat={is_masuk_recorded}, Pulang Tercatat={is_pulang_recorded}, Waktu Masuk: {waktu_masuk_recorded}")

            # Logika untuk absen masuk
            if not is_masuk_recorded: # Coba absen masuk
                # Memeriksa jika sudah melewati jam pulang untuk absen masuk
                if current_time_only > JAM_PULANG:
                    pesan_speak = f"Maaf, {nama_pengabsen_display}, Anda tidak bisa absen masuk karena sudah melewati jam pulang hari ini."
                    tipe_absen_to_php = "gagal" # Tandai sebagai gagal agar tidak dikirim ke PHP
                else:
                    target_masuk_dt = datetime.combine(current_datetime.date(), JAM_MASUK)

                    if current_datetime <= target_masuk_dt:
                        status_action = "TEPAT WAKTU"
                        tipe_absen_to_php = "masuk"
                        pesan_speak = f"Halo {nama_pengabsen_display}, Absen Masuk Tepat Waktu! Selamat datang!"
                    else: # Jika current_datetime > target_masuk_dt (sudah terlambat)
                        selisih = current_datetime - target_masuk_dt
                        total_seconds_late = int(selisih.total_seconds())

                        # Menghitung detail keterlambatan
                        jam_terlambat = int(total_seconds_late / 3600)
                        sisa_detik = total_seconds_late % 3600
                        menit_terlambat = int(sisa_detik / 60)
                        detik_terlambat = int(sisa_detik % 60)

                        terlambat_str = ""
                        if jam_terlambat > 0:
                            terlambat_str += f"{jam_terlambat}jam "
                        if menit_terlambat > 0:
                            terlambat_str += f"{menit_terlambat}menit "
                        terlambat_str += f"{detik_terlambat}detik"

                        status_action = f"TERLAMBAT ({terlambat_str.strip()})"
                        tipe_absen_to_php = "masuk" # Tetap "masuk" walaupun terlambat
                        pesan_speak = f"Halo {nama_pengabsen_display}, Anda Absen Masuk Terlambat {terlambat_str.strip()}."

            # Logika untuk absen pulang
            elif not is_pulang_recorded: # Coba absen pulang, setelah absen masuk
                # Memeriksa apakah sudah absen masuk terlebih dahulu
                if not is_masuk_recorded:
                    pesan_speak = f"Maaf, {nama_pengabsen_display} belum absen masuk hari ini. Anda tidak bisa absen pulang."
                    tipe_absen_to_php = "gagal"
                else:
                    target_pulang_dt = datetime.combine(current_datetime.date(), JAM_PULANG)

                    if current_datetime >= target_pulang_dt:
                        status_action = "PULANG"
                        tipe_absen_to_php = "pulang"
                        pesan_speak = f"Terima kasih {nama_pengabsen_display}, Absen Pulang Berhasil! Sampai jumpa besok."
                    else:
                        selisih = target_pulang_dt - current_datetime
                        jam_lebih_awal = int(selisih.total_seconds() / 3600)
                        menit_lebih_awal = int((selisih.total_seconds() % 3600) / 60)
                        status_action = f"PULANG LEBIH AWAL ({jam_lebih_awal}jam {menit_lebih_awal}menit)"
                        tipe_absen_to_php = "pulang"
                        pesan_speak = f"Maaf, {nama_pengabsen_display} Absen Pulang Lebih Awal {jam_lebih_awal} jam {menit_lebih_awal} menit."

            # Jika sudah absen masuk dan pulang untuk hari ini
            else:
                pesan_speak = f"Maaf, {nama_pengabsen_display} sudah melakukan absen masuk dan pulang hari ini."
                tipe_absen_to_php = "gagal" # Ini akan mencegah pengiriman ke PHP

            # Mengirim data presensi ke server PHP jika bukan status "gagal"
            if tipe_absen_to_php != "gagal":
                print(f"Mencoba mengirim data presensi: User ID={user_id_recognized}, Tipe={tipe_absen_to_php}, Status={status_action}")
                url = 'http://localhost/presensi_wajah/php/input.php'
                data_to_send = {
                    'user_id': user_id_recognized,
                    'tanggal_absen': date_for_db,
                    'waktu_absen': time_for_db,
                    'tipe_absen': tipe_absen_to_php,
                    'status': status_action
                }
                try:
                    x = requests.post(url, data=data_to_send)
                    server_response = x.text.strip()
                    print(f"Respons server untuk presensi: {server_response}")

                    if server_response == 'berhasil':
                        # Memperbarui cache absen_hari_ini setelah operasi database berhasil
                        if tipe_absen_to_php == 'masuk':
                            absen_hari_ini[nama_pengabsen_display] = {'masuk': True, 'pulang': False, 'waktu_masuk': time_for_db}
                        elif tipe_absen_to_php == 'pulang':
                            if nama_pengabsen_display not in absen_hari_ini:
                                absen_hari_ini[nama_pengabsen_display] = {'masuk': False, 'pulang': False, 'waktu_masuk': None}
                            absen_hari_ini[nama_pengabsen_display]['pulang'] = True
                        speak(pesan_speak) # Mengucapkan pesan yang sudah disiapkan
                    elif server_response == 'sudah': # Server menandakan sudah absen (terdeteksi dari DB)
                        speak(f"Maaf, {nama_pengabsen_display} sudah melakukan absen " + ("masuk" if tipe_absen_to_php == 'masuk' else "pulang") + " hari ini.")
                    elif server_response == 'belum_masuk': # Server menandakan belum absen masuk (untuk absen pulang)
                        speak(f"Maaf, {nama_pengabsen_display} belum absen masuk hari ini.")
                    elif "gagal" in server_response:
                        speak(f"Absen Gagal, Tolong Coba Lagi! Pesan Server: {server_response}")
                    else:
                        speak(f"Absen Gagal, Respons tak terduga dari server: {server_response}")
                except requests.exceptions.ConnectionError:
                    print("ConnectionError: Tidak dapat terhubung ke server PHP. Pastikan server XAMPP berjalan.")
                    speak("Tidak dapat terhubung ke server absen. Pastikan XAMPP berjalan.")
                except Exception as e:
                    print(f"Terjadi kesalahan saat presensi (Python): {e}")
                    speak("Terjadi kesalahan saat absen. Coba lagi!")

            else: # tipe_absen_to_php == "gagal" (dari validasi Python)
                speak(pesan_speak) # Mengucapkan pesan yang sudah disiapkan

            # Mengatur ulang status kedipan dan senyum untuk deteksi berikutnya
            kedip = 'X'
            color_kedip = (0,0,255)
            senyum = 'X'
            color_senyum = (0,0,255)
        else: # Wajah tidak dikenali atau data pengguna hilang
            print(f"Kondisi absen tidak terpenuhi. Nama Tampilan: {nama_pengabsen_display}, ID Pengguna: {user_id_recognized}")
            speak("Maaf, Anda belum terdaftar!")
            # Mengatur ulang status kedipan dan senyum
            kedip = 'X'
            color_kedip = (0,0,255)
            color_senyum = (0,0,255)
            senyum = 'X'

    # Menghentikan program jika tombol 'q' ditekan
    if k == ord('q'):
        print("Tombol 'q' ditekan. Keluar dari program.")
        break

# Melepaskan sumber daya kamera dan menutup semua jendela OpenCV
video.release()
cv2.destroyAllWindows()
print("Program dihentikan.")
