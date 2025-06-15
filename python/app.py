import os
import subprocess
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import threading
import requests
import json
import uuid
from datetime import datetime, timedelta
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = 'super_secret_key_anda_yang_kuat' # Pastikan ini adalah kunci rahasia yang kuat dan unik

# Path ke skrip Python
PYTHON_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ADD_FACES_SCRIPT = os.path.join(PYTHON_SCRIPTS_DIR, 'add_faces.py')
REMOVE_FACE_DATA_SCRIPT = os.path.join(PYTHON_SCRIPTS_DIR, 'remove_face_data.py')

# Variabel global untuk status penangkapan wajah
capture_process = None
capture_status_message = ""
current_face_id = ""
current_user_name = ""
capture_outcome = None # Tambahan: Menyimpan hasil akhir proses (None, 'success', 'failure')

# URL untuk interaksi dengan skrip PHP
PHP_REGISTER_URL = 'http://localhost/presensi_wajah/php/register.php'
PHP_GET_USER_DETAILS_URL = 'http://localhost/presensi_wajah/php/get_user_details.php'
PHP_GET_ALL_USERS_URL = 'http://localhost/presensi_wajah/php/get_all_users.php'
PHP_EDIT_USER_URL = 'http://localhost/presensi_wajah/php/edit_user.php'
PHP_DELETE_USER_URL = 'http://localhost/presensi_wajah/php/delete_user.php'
PHP_GET_ATTENDANCE_URL = 'http://localhost/presensi_wajah/php/getData.php'


# --- FUNGSI get_user_details_from_db di app.py ---
def get_user_details_from_db(user_id=None, face_id=None):
    """
    Mengambil detail pengguna dari database melalui PHP.
    Bisa berdasarkan user_id atau face_id.
    """
    url = PHP_GET_USER_DETAILS_URL
    params = {}
    if user_id:
        params['user_id'] = user_id
    elif face_id:
        params['face_id'] = face_id
    else:
        return None

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # Akan memunculkan HTTPError untuk status kode 4xx/5xx
        user_data = response.json()
        if user_data and 'error' not in user_data:
            return user_data # Mengembalikan dictionary user details
        print(f"Error from PHP get_user_details_from_db: {user_data.get('error', 'Unknown error')}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user details from PHP: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON from PHP get_user_details_from_db. Response: {response.text}")
        return None

# --- FUNGSI get_all_users_from_db di app.py ---
def get_all_users_from_db():
    """
    Mengambil semua data pengguna dari database melalui PHP.
    """
    url = PHP_GET_ALL_USERS_URL
    try:
        response = requests.get(url)
        response.raise_for_status()
        users_data_raw = response.json()

        if isinstance(users_data_raw, dict) and 'error' in users_data_raw:
            print(f"Error from PHP get_all_users_from_db: {users_data_raw.get('error', 'Unknown error')}")
            return [] # Kembalikan list kosong jika PHP mengembalikan error
        else:
            return users_data_raw # Mengembalikan list data pengguna (atau list kosong)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching all users from PHP: {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from PHP get_all_users_from_db. Raw response: {response.text}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register_user', methods=['GET', 'POST'])
def register_user():
    global current_face_id, current_user_name
    # Mendapatkan tanggal hari ini dalam format大全-MM-DD untuk atribut max
    today = datetime.now().strftime('%Y-%m-%d')

    # Inisialisasi variabel untuk mempertahankan nilai form
    nama = ''
    alamat = ''
    no_hp = ''
    tanggal_lahir = ''
    jenis_kelamin = ''

    if request.method == 'POST':
        nama = request.form['nama'].strip()
        alamat = request.form['alamat'].strip()
        no_hp = request.form['no_hp'].strip()
        tanggal_lahir = request.form['tanggal_lahir']
        jenis_kelamin = request.form['jenis_kelamin']

        # =====================================================================
        # Validasi Sisi Server untuk Registrasi (Wajib Diisi & Format)
        # =====================================================================
        errors = []

        # Validasi Nama: tidak boleh kosong, hanya huruf dan spasi
        if not nama:
            errors.append("Nama tidak boleh kosong.")
        elif not all(c.isalpha() or c.isspace() for c in nama):
            errors.append("Nama hanya boleh berisi huruf dan spasi.")
        
        # Validasi Alamat: tidak boleh kosong
        if not alamat:
            errors.append("Alamat tidak boleh kosong.")

        # Validasi Nomor HP: tidak boleh kosong, hanya angka, dan panjang 10-15 digit
        if not no_hp:
            errors.append("Nomor HP tidak boleh kosong.")
        elif not (no_hp.isdigit() and 10 <= len(no_hp) <= 15):
            errors.append("Nomor HP harus berupa angka dan memiliki panjang antara 10 sampai 15 digit.")
        
        # Validasi Tanggal Lahir: tidak boleh kosong, format valid, dan tidak di masa depan
        if not tanggal_lahir:
            errors.append("Tanggal lahir tidak boleh kosong.")
        else:
            try:
                parsed_date = datetime.strptime(tanggal_lahir, "%Y-%m-%d").date()
                if parsed_date > datetime.now().date():
                    errors.append("Tanggal lahir tidak boleh di masa depan.")
            except ValueError:
                errors.append("Format tanggal lahir tidak valid.")
        
        # Validasi Jenis Kelamin: tidak boleh kosong dan pilihan valid
        if not jenis_kelamin:
            errors.append("Jenis kelamin tidak boleh kosong.")
        elif jenis_kelamin not in ['Laki-laki', 'Perempuan']:
            errors.append("Pilihan jenis kelamin tidak valid.")

        if errors:
            for error in errors:
                flash(error, 'error')
            # Kembalikan nilai form yang sudah diisi agar pengguna tidak perlu mengisi ulang
            return render_template('register_user.html', 
                                   today=today, 
                                   nama=nama, 
                                   alamat=alamat, 
                                   no_hp=no_hp, 
                                   tanggal_lahir=tanggal_lahir, 
                                   jenis_kelamin=jenis_kelamin)

        # Jika semua validasi berhasil, lanjutkan proses
        face_id = str(uuid.uuid4()) # Generate face_id unik

        register_data = {
            'nama': nama,
            'alamat': alamat,
            'no_hp': no_hp,
            'tanggal_lahir': tanggal_lahir,
            'jenis_kelamin': jenis_kelamin,
            'face_id': face_id
        }
        
        try:
            response_php = requests.post(PHP_REGISTER_URL, data=register_data)
            response_php.raise_for_status()
            php_result = response_php.text.strip()

            if php_result.startswith("berhasil_daftar_dengan_id:"):
                user_id_from_php = php_result.split(":")[1]
                current_face_id = face_id
                current_user_name = nama
                flash(f"Data diri {nama} berhasil disimpan. Sekarang, silakan lakukan penangkapan wajah.", 'success')
                return redirect(url_for('add_face_capture', face_id=face_id, user_name=nama))
            else:
                flash(f"Gagal menyimpan data diri: {php_result}", 'error')
                # Kembalikan nilai form yang sudah diisi
                return render_template('register_user.html', 
                                       today=today, 
                                       nama=nama, 
                                       alamat=alamat, 
                                       no_hp=no_hp, 
                                       tanggal_lahir=tanggal_lahir, 
                                       jenis_kelamin=jenis_kelamin)
        except requests.exceptions.ConnectionError:
            flash("Tidak dapat terhubung ke server PHP. Pastikan XAMPP berjalan.", 'error')

    return render_template('register_user.html', today=today, nama=nama, alamat=alamat, no_hp=no_hp, tanggal_lahir=tanggal_lahir, jenis_kelamin=jenis_kelamin)

@app.route('/add_face_capture/<face_id>/<user_name>', methods=['GET'])
def add_face_capture(face_id, user_name):
    global capture_process, capture_status_message, current_face_id, current_user_name, capture_outcome # Tambahkan capture_outcome

    # Reset status dan outcome saat memulai proses baru
    capture_process = None
    capture_status_message = ""
    capture_outcome = None # Reset outcome

    capture_status_message = f"Memulai penangkapan wajah untuk {user_name} (ID: {face_id})..."
    flash(f"Memulai proses penangkapan wajah untuk {user_name}. Silakan lihat kamera.", 'info')

    def run_add_faces(face_id_arg, user_name_arg):
        global capture_process, capture_status_message, capture_outcome
        try:
            command = ['python', ADD_FACES_SCRIPT, face_id_arg, user_name_arg]
            process_result = subprocess.run(command, capture_output=True, text=True, check=True) # Simpan hasil proses
            
            if process_result.returncode == 0:
                capture_status_message = f"Penangkapan wajah untuk {user_name_arg} (ID: {face_id_arg}) selesai! Output: {process_result.stdout}"
                capture_outcome = 'success' # Set outcome sukses
            else:
                capture_status_message = f"Penangkapan wajah untuk {user_name_arg} (ID: {face_id_arg}) gagal! Error: {process_result.stderr}"
                capture_outcome = 'failure' # Set outcome gagal
        except subprocess.CalledProcessError as e:
            capture_status_message = f"Error saat menjalankan skrip: {e.stderr}"
            capture_outcome = 'failure' # Set outcome gagal
        except FileNotFoundError:
            capture_status_message = "Error: Python executable atau add_faces.py tidak ditemukan."
            capture_outcome = 'failure' # Set outcome gagal
        except Exception as e:
            capture_status_message = f"Error tak terduga: {str(e)}"
            capture_outcome = 'failure' # Set outcome gagal
        finally:
            capture_process = None # Pastikan proses direset setelah selesai

    thread = threading.Thread(target=run_add_faces, args=(face_id, user_name,))
    thread.start()
    
    return render_template('add_face_capture.html', status=capture_status_message, face_id=face_id, user_name=user_name)

@app.route('/status_add_face')
def status_add_face():
    global capture_status_message, current_face_id, current_user_name, capture_outcome
    # Mengembalikan status, apakah proses masih berjalan, face_id, user_name, dan outcome
    return {
        'status': capture_status_message,
        'is_running': capture_process is not None,
        'face_id': current_face_id,
        'user_name': current_user_name,
        'outcome': capture_outcome # Tambahan: Mengembalikan outcome
    }

# --- Rute display_attendance ---
@app.route('/display_attendance', methods=['GET'])
def display_attendance():
    attendance_data = []
    selected_date = request.args.get('tanggal')

    php_url = PHP_GET_ATTENDANCE_URL
    params = {}
    if selected_date:
        params['tanggal'] = selected_date

    try:
        response = requests.get(php_url, params=params)
        response.raise_for_status()
        attendance_data = response.json()
        
    except requests.exceptions.ConnectionError:
        flash("Tidak dapat terhubung ke server PHP. Pastikan XAMPP berjalan.", 'error')
    except requests.exceptions.HTTPError as e:
        flash(f"Error HTTP saat mengambil data: {e}", 'error')
    except json.JSONDecodeError:
        flash("Gagal memparsing respons JSON dari server PHP. Pastikan getData.php mengeluarkan JSON yang valid.", 'error')
    except Exception as e:
        flash(f"Terjadi kesalahan tak terduga: {e}", 'error')

    today_date = datetime.now().strftime('%Y-%m-%d')

    return render_template('display_attendance.html', attendance_data=attendance_data, selected_date=selected_date, today_date=today_date)

# --- Rute: Manajemen Pengguna ---
@app.route('/manage_users')
def manage_users():
    users_data = get_all_users_from_db()
    return render_template('manage_users.html', users=users_data)


# --- Rute Edit User ---
@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    # Mendapatkan tanggal hari ini dalam format大全-MM-DD untuk atribut max
    today = datetime.now().strftime('%Y-%m-%d')

    user_details = get_user_details_from_db(user_id=user_id)

    if not user_details:
        flash(f"Pengguna dengan ID {user_id} tidak ditemukan atau ada kesalahan.", 'error')
        return redirect(url_for('manage_users'))

    if request.method == 'POST':
        nama = request.form['nama'].strip()
        alamat = request.form['alamat'].strip()
        no_hp = request.form['no_hp'].strip()
        tanggal_lahir = request.form['tanggal_lahir']
        jenis_kelamin = request.form['jenis_kelamin']

        # =====================================================================
        # Validasi Sisi Server untuk Edit User (Wajib Diisi & Format)
        # =====================================================================
        errors = []

        # Validasi Nama: tidak boleh kosong, hanya huruf dan spasi
        if not nama:
            errors.append("Nama tidak boleh kosong.")
        elif not all(c.isalpha() or c.isspace() for c in nama):
            errors.append("Nama hanya boleh berisi huruf dan spasi.")
        
        # Validasi Alamat: tidak boleh kosong
        if not alamat:
            errors.append("Alamat tidak boleh kosong.")

        # Validasi Nomor HP: tidak boleh kosong, hanya angka, dan panjang 10-15 digit
        if not no_hp:
            errors.append("Nomor HP tidak boleh kosong.")
        elif not (no_hp.isdigit() and 10 <= len(no_hp) <= 15):
            errors.append("Nomor HP harus berupa angka dan memiliki panjang antara 10 sampai 15 digit.")
        
        # Validasi Tanggal Lahir: tidak boleh kosong, format valid, dan tidak di masa depan
        if not tanggal_lahir:
            errors.append("Tanggal lahir tidak boleh kosong.")
        else:
            try:
                parsed_date = datetime.strptime(tanggal_lahir, "%Y-%m-%d").date()
                if parsed_date > datetime.now().date():
                    errors.append("Tanggal lahir tidak boleh di masa depan.")
            except ValueError:
                errors.append("Format tanggal lahir tidak valid.")
        
        # Validasi Jenis Kelamin: tidak boleh kosong dan pilihan valid
        if not jenis_kelamin:
            errors.append("Jenis kelamin tidak boleh kosong.")
        elif jenis_kelamin not in ['Laki-laki', 'Perempuan']:
            errors.append("Pilihan jenis kelamin tidak valid.")

        if errors:
            for error in errors:
                flash(error, 'error')
            # Kembalikan nilai form yang sudah diisi
            user_details['nama'] = nama
            user_details['alamat'] = alamat
            user_details['no_hp'] = no_hp
            user_details['tanggal_lahir'] = tanggal_lahir
            user_details['jenis_kelamin'] = jenis_kelamin
            return render_template('edit_user.html', user=user_details, today=today)

        # Jika semua validasi berhasil, kirim data ke PHP
        update_data = {
            'user_id': user_id,
            'nama': nama,
            'alamat': alamat,
            'no_hp': no_hp,
            'tanggal_lahir': tanggal_lahir,
            'jenis_kelamin': jenis_kelamin
        }
        try:
            response_php = requests.post(PHP_EDIT_USER_URL, data=update_data)
            response_php.raise_for_status()
            php_result = response_php.text.strip()

            if php_result == 'berhasil':
                flash('Data pengguna berhasil diperbarui!', 'success')
                return redirect(url_for('manage_users'))
            else:
                flash(f"Gagal memperbarui data pengguna: {php_result}", 'error')
                user_details = get_user_details_from_db(user_id=user_id) # Ambil ulang data jika ada error
                return render_template('edit_user.html', user=user_details, today=today)
        except requests.exceptions.ConnectionError:
            flash("Tidak dapat terhubung ke server PHP.", 'error')
        except Exception as e:
            flash(f"Terjadi kesalahan tak terduga saat memperbarui: {e}", 'error')
        
        user_details = get_user_details_from_db(user_id=user_id) # Ambil ulang data jika ada error
        return render_template('edit_user.html', user=user_details, today=today)
    
    return render_template('edit_user.html', user=user_details, today=today)

# --- Rute Hapus User ---
@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    face_id_to_delete = None
    user_name_to_delete = None # Variabel baru untuk menyimpan nama pengguna

    user_details = get_user_details_from_db(user_id=user_id)
    
    # Pastikan 'nama' juga ada di user_details
    if user_details and 'face_id' in user_details and 'nama' in user_details:
        face_id_to_delete = user_details['face_id']
        user_name_to_delete = user_details['nama'] # Dapatkan nama pengguna
    else:
        flash(f"Error: Tidak dapat menemukan Face ID atau Nama untuk User ID {user_id}. Penghapusan data wajah mungkin tidak dilakukan.", 'error')
        face_id_to_delete = None
        user_name_to_delete = None

    delete_url = PHP_DELETE_USER_URL
    delete_data = {'user_id': user_id}
    try:
        response_php = requests.post(delete_url, data=delete_data)
        response_php.raise_for_status()
        php_result = response_php.text.strip()

        if php_result == 'berhasil':
            flash('Pengguna dan semua catatan presensinya berhasil dihapus!', 'success')
            # Pastikan face_id dan user_name tersedia sebelum memanggil skrip Python
            if face_id_to_delete and user_name_to_delete:
                def run_remove_face_data(face_id_arg, user_name_arg): # Teruskan user_name_arg
                    try:
                        # Teruskan face_id dan user_name ke skrip remove_face_data.py
                        command = ['python', REMOVE_FACE_DATA_SCRIPT, face_id_arg, user_name_arg]
                        subprocess.run(command, check=True, capture_output=True)
                        print(f"Face data and captured images for {user_name_arg} ({face_id_arg}) removed.")
                    except subprocess.CalledProcessError as e:
                        print(f"Error removing face data for {user_name_arg} ({face_id_arg}): {e.stderr}")
                    except Exception as e:
                        print(f"Unexpected error during face data removal: {e}")
                
                # Mulai thread dengan kedua argumen
                threading.Thread(target=run_remove_face_data, args=(face_id_to_delete, user_name_to_delete,)).start()
            
            return redirect(url_for('manage_users'))
        else:
            flash(f"Gagal menghapus pengguna: {php_result}", 'error')
            return redirect(url_for('manage_users'))
    except requests.exceptions.ConnectionError:
        flash("Tidak dapat terhubung ke server PHP.", 'error')
    except Exception as e:
        flash(f"Terjadi kesalahan tak terduga saat menghapus: {e}", 'error')
    
    return redirect(url_for('manage_users'))

# --- Rute Ekspor Excel ---
@app.route('/export_attendance_excel', methods=['GET'])
def export_attendance_excel():
    selected_date = request.args.get('date_param') # Ambil tanggal dari parameter URL

    php_url = PHP_GET_ATTENDANCE_URL
    params = {}
    if selected_date:
        params['tanggal'] = selected_date

    try:
        response = requests.get(php_url, params=params)
        response.raise_for_status()
        attendance_data = response.json()

        if isinstance(attendance_data, dict) and 'error' in attendance_data:
            flash(f"Error saat mengambil data presensi untuk ekspor: {attendance_data['error']}", 'error')
            return redirect(url_for('display_attendance', tanggal=selected_date))
        
        if not attendance_data:
            flash("Tidak ada data presensi untuk diekspor pada tanggal ini.", 'info')
            return redirect(url_for('display_attendance', tanggal=selected_date))

        # Konversi list of dicts ke DataFrame Pandas
        df = pd.DataFrame(attendance_data)

        # Ganti nilai kosong dengan '-' untuk tampilan yang lebih baik di Excel
        df = df.fillna('-')

        # Ganti nama kolom agar lebih mudah dibaca di Excel
        df.rename(columns={
            'absen_id': 'ID Absen',
            'nama': 'Nama',
            'tanggal': 'Tanggal',
            'waktu_masuk': 'Waktu Masuk',
            'status_masuk': 'Status Masuk',
            'waktu_pulang': 'Waktu Pulang',
            'status_pulang': 'Status Pulang'
        }, inplace=True)

        # Urutkan kolom sesuai urutan yang diinginkan
        ordered_columns = [
            'ID Absen', 'Nama', 'Tanggal', 'Waktu Masuk', 'Status Masuk',
            'Waktu Pulang', 'Status Pulang'
        ]
        # Pastikan hanya kolom yang ada di DataFrame yang diurutkan
        df = df[df.columns.intersection(ordered_columns)]


        # Buat buffer in-memory untuk menyimpan file Excel
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='Presensi')
        writer.close() # Gunakan close() bukan save() untuk versi pandas terbaru
        output.seek(0) # Kembali ke awal buffer

        # Buat nama file yang dinamis
        filename = f"Rekap_Presensi_{selected_date if selected_date else 'Semua'}.xlsx"

        return send_file(output, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except requests.exceptions.ConnectionError:
        flash("Tidak dapat terhubung ke server PHP untuk mengambil data presensi. Pastikan XAMPP berjalan.", 'error')
    except requests.exceptions.HTTPError as e:
        flash(f"Error HTTP saat mengambil data presensi untuk ekspor: {e}", 'error')
    except json.JSONDecodeError:
        flash("Gagal memparsing respons JSON dari server PHP saat ekspor. Pastikan getData.php mengeluarkan JSON yang valid.", 'error')
    except Exception as e:
        flash(f"Terjadi kesalahan tak terduga saat ekspor data: {e}", 'error')

    return redirect(url_for('display_attendance', tanggal=selected_date))


if __name__ == '__main__':
    app.run(debug=True)
