import pickle
import numpy as np
import os

# Tentukan path ke direktori dasar proyek Anda (misalnya, 'python')
# BASE_DIR akan menjadi c:\xampp\htdocs\presensi_wajah\python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# DATA_DIR seharusnya langsung menunjuk ke folder 'data' di dalam BASE_DIR
# Jadi, DATA_DIR akan menjadi c:\xampp\htdocs\presensi_wajah\python\data
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Sekarang, path ke file .pkl sudah benar
# names_pkl_path akan menjadi c:\xampp\htdocs\presensi_wajah\python\data\names.pkl
names_pkl_path = os.path.join(DATA_DIR, 'names.pkl')
# faces_pkl_path akan menjadi c:\xampp\htdocs\presensi_wajah\python\data\faces.pkl
faces_pkl_path = os.path.join(DATA_DIR, 'faces.pkl')


# --- Membaca names.pkl ---
print("--- Membaca names.pkl ---")
try:
    if not os.path.exists(names_pkl_path):
        print(f"Error: File '{names_pkl_path}' tidak ditemukan. Pastikan sudah ada.")
    elif os.path.getsize(names_pkl_path) == 0:
        print(f"Error: File '{names_pkl_path}' kosong.")
    else:
        with open(names_pkl_path, 'rb') as file:
            labels = pickle.load(file)
            print("Isi names.pkl (Labels):")
            print(labels)
            print(f"\nJumlah total label: {len(labels)}")
except EOFError:
    print(f"Error: File '{names_pkl_path}' rusak atau tidak lengkap.")
except Exception as e:
    print(f"Terjadi kesalahan saat membaca names.pkl: {e}")

print("\n")

# --- Membaca faces.pkl ---
print("--- Membaca faces.pkl ---")
try:
    if not os.path.exists(faces_pkl_path):
        print(f"Error: File '{faces_pkl_path}' tidak ditemukan. Pastikan sudah ada.")
    elif os.path.getsize(faces_pkl_path) == 0:
        print(f"Error: File '{faces_pkl_path}' kosong.")
    else:
        with open(faces_pkl_path, 'rb') as file:
            face_features = pickle.load(file)
            print("Isi faces.pkl (Fitur Wajah - Array NumPy):")
            # Cetak hanya beberapa baris pertama agar tidak terlalu panjang di konsol
            if face_features.size > 0:
                print(face_features[:5]) # Cetak 5 baris pertama
                if len(face_features) > 5:
                    print("...")
            else:
                print("Array fitur wajah kosong.")
            print(f"\nBentuk (shape) array: {face_features.shape}")
            print(f"Jumlah total fitur wajah yang tersimpan: {len(face_features)}")
except EOFError:
    print(f"Error: File '{faces_pkl_path}' rusak atau tidak lengkap.")
except Exception as e:
    print(f"Terjadi kesalahan saat membaca faces.pkl: {e}")