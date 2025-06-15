import pickle
import numpy as np
import os
import sys
import shutil # Import shutil untuk menghapus direktori

# Path ke file .pkl
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

names_pkl_path = os.path.join(DATA_DIR, 'names.pkl')
faces_pkl_path = os.path.join(DATA_DIR, 'faces.pkl')

# Direktori root untuk capture foto wajah
CAPTURES_ROOT_DIR = os.path.join(BASE_DIR, 'captured_faces')

# Ambil face_id dan user_name dari argumen baris perintah
if len(sys.argv) > 2: # Mengharapkan 2 argumen: face_id dan user_name_raw
    face_id_to_remove = sys.argv[1]
    user_name_raw = sys.argv[2]
    
    # Bersihkan user_name agar aman untuk nama folder (sama seperti di add_faces.py)
    # Ini penting agar nama folder yang dibuat dan yang akan dihapus konsisten
    user_name_clean = "".join(c for c in user_name_raw if c.isalnum() or c.isspace()).strip()
    user_name_folder = user_name_clean.replace(" ", "_")
    
    # Buat nama folder yang diharapkan untuk dihapus
    USER_CAPTURE_DIR_TO_REMOVE = os.path.join(CAPTURES_ROOT_DIR, f"{user_name_folder}_{face_id_to_remove}")
else:
    print("Error: face_id and user_name not provided as arguments. Usage: python remove_face_data.py <face_id> <user_name>")
    sys.exit(1)

# --- Hapus data dari PKL files ---
try:
    # Muat data yang ada
    # Periksa apakah file PKL ada dan tidak kosong sebelum mencoba membukanya
    if os.path.exists(names_pkl_path) and os.path.getsize(names_pkl_path) > 0:
        with open(names_pkl_path, 'rb') as f:
            names = pickle.load(f)
    else:
        names = [] # Jika file tidak ada atau kosong, anggap list kosong

    if os.path.exists(faces_pkl_path) and os.path.getsize(faces_pkl_path) > 0:
        with open(faces_pkl_path, 'rb') as f:
            faces = pickle.load(f)
    else:
        faces = np.array([]) # Jika file tidak ada atau kosong, anggap array kosong

    # Temukan indeks yang sesuai dengan face_id yang akan dihapus
    indices_to_remove = [i for i, label in enumerate(names) if label == face_id_to_remove]

    if not indices_to_remove:
        print(f"Face ID {face_id_to_remove} not found in PKL files. No data removed from PKL.")
    else:
        # Hapus entri dari names dan faces
        new_names = [name for i, name in enumerate(names) if i not in indices_to_remove]
        
        # Pastikan faces tidak kosong sebelum mencoba np.delete
        if faces.size > 0:
            new_faces = np.delete(faces, indices_to_remove, axis=0)
        else:
            new_faces = np.array([]) # Jika faces kosong, biarkan kosong

        # Simpan kembali data yang sudah diperbarui
        with open(names_pkl_path, 'wb') as f:
            pickle.dump(new_names, f)
        with open(faces_pkl_path, 'wb') as f:
            pickle.dump(new_faces, f)
        print(f"Face data for {face_id_to_remove} successfully removed from PKL files.")

except FileNotFoundError:
    print("Error: names.pkl or faces.pkl not found. No data to remove from PKL.")
except Exception as e:
    print(f"An error occurred during PKL removal: {e}")

# --- Hapus folder gambar wajah yang di-capture ---
if os.path.exists(USER_CAPTURE_DIR_TO_REMOVE):
    try:
        shutil.rmtree(USER_CAPTURE_DIR_TO_REMOVE)
        print(f"Captured face images folder '{USER_CAPTURE_DIR_TO_REMOVE}' successfully removed.")
    except OSError as e:
        print(f"Error removing captured face images folder '{USER_CAPTURE_DIR_TO_REMOVE}': {e}")
else:
    print(f"Captured face images folder '{USER_CAPTURE_DIR_TO_REMOVE}' not found. No folder removed.")

sys.exit(0) # Keluar dengan sukses
