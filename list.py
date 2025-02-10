import tkinter as tk
import requests
import configparser
import os
import threading
from tkinter import ttk, messagebox
from dotenv import load_dotenv
from typing import Iterator

# import sdk reader hw family series
from response import hex_readable, Response
from reader import Reader
from transport import SerialTransport, TcpTransport
from serial.serialutil import PortNotOpenError

# import sdk reader rc4 family series
from rfid.response import Tag
from rfid.reader import ReaderRC4, StopType
from rfid.transport import TransportRC4, TcpTransportRC4

from ui.thread.output_control_thread import (SetManualRelayThread, SetAutoRelayThread, GetOutputControlThread)

import socket
import sys

load_dotenv()

# Function to get saved token
def get_saved_token():
    config = configparser.ConfigParser()
    if not os.path.exists('config.ini'):
        return ''
    try:
        config.read('config.ini')
        return config['DEFAULT'].get('token')
    except (configparser.Error, KeyError):
        return ''

# Function to get all tag readers
def get_all_tag_readers():
    token = get_saved_token()
    if not token:
        messagebox.showerror("Error", "Token not found. Please login.")
        return []

    list_url = os.getenv('LIST_URL')
    api_key = os.getenv('API_KEY')
    headers = {'X-API-KEY': api_key, 'X-Token': token}

    try:
        response = requests.get(list_url, headers=headers)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", str(e))
        return []

    if result.get('status'):
        tag_readers = result['data'].get('tag_reader', [])

        if isinstance(tag_readers, list):
            return tag_readers
        else:
            messagebox.showerror("Error", "Unexpected data format received")
            return []
    else:
        messagebox.showerror("Error", result.get('message', 'Unknown error'))
        return []
    
# Function to get status aset
def get_status_aset(rfid_tag_number):
    token = get_saved_token()
    if not token:
        messagebox.showerror("Error", "Token not found. Please login.")
        return []

    list_url = f"{os.getenv('GETASETSTATUS')}?filter={rfid_tag_number}&field=&start=&limit=&sort_field=&sort_order=ASC"
    api_key = os.getenv('API_KEY')
    headers = {'X-API-KEY': api_key, 'X-Token': token}

    try:
        response = requests.get(list_url, headers=headers)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", str(e))
        return []
    
    if result.get('status'):
        tb_master_aset = result['data'].get('tb_master_aset', [])
        # print(tb_master_aset)  # Menampilkan isi dari tb_master_aset

        if isinstance(tb_master_aset, list):
            return tb_master_aset
        else:
            messagebox.showerror("Error", "Unexpected data format received")
            return []
    else:
        messagebox.showerror("Error", result.get('message', 'Unknown error'))
        return []

# Function to create label and entry widget
def create_label_and_entry(frame, row, label_text, default_value, is_editable=False):
    label = tk.Label(frame, text=label_text, padx=10, pady=5, anchor='w')
    label.grid(row=row, column=0, sticky='w')
    entry = ttk.Entry(frame)
    entry.insert(0, default_value)
    if not is_editable:
        entry.configure(state='disabled')
    entry.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
    return label, entry

# Function to handle type change (serial or tcp)
def on_type_change(type_var, serial_widgets, tcp_widgets):
    reader_type = type_var.get()
    if reader_type == 'serial':
        for widget in serial_widgets:
            widget.grid()
        for widget in tcp_widgets:
            widget.grid_remove()
    elif reader_type == 'tcp':
        for widget in tcp_widgets:
            widget.grid()
        for widget in serial_widgets:
            widget.grid_remove()

# Main function to show list page
def list_page():
    def go_to_dashboard():
        root.destroy()
        import dashboard
        dashboard.show_dashboard()

    # Dictionary to hold connection and mode status for each reader
    reader_status = {}

    def toggle_connection(reader_id, status_label):

        reader_name = reader_status[reader_id]['name']
        reader_family = reader_status[reader_id]['reader_family']

        if reader_status[reader_id]['connected']:

            reader_status[reader_id]['connected'] = False
            reader_status[reader_id]['reading_enabled'] = False
            reader_status[reader_id]['mode'] = "Read Mode"
            connect_button = reader_status[reader_id]['connect_button']
            mode_button = reader_status[reader_id]['mode_button']

            # Update tombol dan status label saat reader disconnect, kemudian disable tombol mode
            connect_button.configure(text="Connect", width=12)
            mode_button.configure(text="Read Mode", state=tk.DISABLED, width=12)
            
            # Disable treeview when reader is disconnected
            toggle_treeview(reader_id, mode_button.cget("text"))

            status_label.configure(text="Reader Disconnected", bg="red", fg="white")
            # messagebox.showinfo("Info", f"Disconnected from {reader_name}")

        else:

            #messagebox.showinfo("Info", f"Create connection to {reader_family}")

            if (reader_family == "RC4"):
                reader_instance = create_transport(reader_id, reader_family)

                if reader_instance:
                    reader_status[reader_id]['instance'] = reader_instance
                    reader_status[reader_id]['connected'] = True
                    reader_status[reader_id]['reading_enabled'] = False
                    connect_button = reader_status[reader_id]['connect_button']
                    mode_button = reader_status[reader_id]['mode_button']

                    # Update tombol dan status label saat reader connect
                    connect_button.configure(text="Disconnect", width=12)
                    mode_button.configure(state=tk.NORMAL)
                    
                    # Enable treeview when reader is connected
                    toggle_treeview(reader_id, mode_button.cget("text"))

                    status_label.configure(text="Reader Connected", bg="green", fg="white")
                    # messagebox.showinfo("Info", f"Connected to {reader_name}")

                else:
                    messagebox.showerror("Error", f"Failed to connect to {reader_name}")

            else:

                reader_instance = create_transport(reader_id, reader_family)

                if reader_instance:
                    reader_status[reader_id]['instance'] = reader_instance
                    reader_status[reader_id]['connected'] = True
                    reader_status[reader_id]['reading_enabled'] = False
                    connect_button = reader_status[reader_id]['connect_button']
                    mode_button = reader_status[reader_id]['mode_button']

                    # Update tombol dan status label saat reader connect
                    connect_button.configure(text="Disconnect", width=12)
                    mode_button.configure(state=tk.NORMAL)
                    
                    # Enable treeview when reader is connected
                    toggle_treeview(reader_id, mode_button.cget("text"))

                    status_label.configure(text="Reader Connected", bg="green", fg="white")
                    # messagebox.showinfo("Info", f"Connected to {reader_name}")

                else:
                    messagebox.showerror("Error", f"Failed to connect to {reader_name}")

    def toggle_mode(reader_id):
        reader_name = reader_status[reader_id]['name']
        reader_instance = reader_status[reader_id]['instance']
        reader_mode = reader_status[reader_id]['reader_mode']
        treeview = reader_status[reader_id]['treeview']

        if reader_status[reader_id]['connected']:
            if reader_status[reader_id]['mode'] == "Read Mode":

                # Start reading
                reader_status[reader_id]['mode'] = "Unread Mode"
                reader_status[reader_id]['reading_enabled'] = True

                # Update tombol mode, 'mode': "Read Mode / Unread Mode",
                mode_button = reader_status[reader_id]['mode_button']
                mode_button.configure(text="Unread Mode", width=12)

                # enabled / disabled treeview
                toggle_treeview(reader_id, reader_status[reader_id]['mode'])

                # messagebox.showinfo("Info", f"{reader_name} is now in Unread Mode")

                # Buat thread untuk membaca data dari reader
                # dan jalankan thread secara daemon agar thread
                # dapat berhenti jika aplikasi dihentikan
                reader_thread = threading.Thread(target=start_reading, args=(reader_id, root))
                reader_thread.daemon = True
                reader_thread.start()
                reader_status[reader_id]['thread'] = reader_thread
            else:
                reader_status[reader_id]['mode'] = "Read Mode"
                reader_status[reader_id]['reading_enabled'] = False
                mode_button = reader_status[reader_id]['mode_button']
                mode_button.configure(text="Read Mode", width=12)
                treeview.delete(*treeview.get_children())  # Clear the Treeview
                toggle_treeview(reader_id, reader_status[reader_id]['mode'])

    def toggle_treeview(reader_id, mode):
        if mode == "Read Mode":
            reader_status[reader_id]['treeview']["style"] = "enabled.Treeview"
        else:
            reader_status[reader_id]['treeview']["style"] = "disabled.Treeview"

    def create_transport(reader_id, reader_family):
        tag_readers = get_all_tag_readers()
        for reader in tag_readers:
            if isinstance(reader, dict) and reader.get('reader_id') == reader_id:
                reader_type = reader.get('reader_type', '')

                try:
                    if reader_type == 'serial':
                        com_port = reader.get('reader_com', '')
                        baud_rate = reader.get('reader_baudrate', '')
                        transport = SerialTransport(com_port, int(baud_rate))
                        reader_instance = Reader(transport)
                        return reader_instance

                    elif reader_type == 'tcp':

                        ip_address = reader.get('reader_ip', '')
                        port = reader.get('reader_port', '')
                        # messagebox.showinfo("Info", f"Connecting to {ip_address}:{port}", parent=root)

                        if reader_family == 'hw':
                            transport = TcpTransport(ip_address, int(port))
                            reader_instance = Reader(transport)
                        elif reader_family == 'rc':
                            try:
                            # Setup transport instance

                                # transportRC4 = TcpTransportRC4('192.168.1.200', 2022)
                                # reader_status[1]['instance'] = ReaderRC4(transportRC4)
                                transportRC4 = TcpTransportRC4(ip_address, int(port))
                                reader_instance = ReaderRC4(transportRC4)

                            except Exception as e:
                                messagebox.showerror("Error", f"Failed to initialize transport: {str(e)}")
                                return  # Berhenti jika inisialisasi transport gagal

                        return reader_instance

                except Exception as e:
                    messagebox.showerror("Error", str(e))
                    return None
        messagebox.showerror("Error", "Reader configuration not found.")
        return None

    def start_reading(reader_id, root):
        def show_error_message(error_message):
            print('')
            # messagebox.showerror("Error Mboh", error_message)

        # Reset timer untuk reader, fungsi ini dipanggil setiap kali
        # reader selesai membaca dan sebelum mulai membaca lagi.
        # Ini digunakan untuk memastikan reader tidak membaca terlalu cepat
        # dan memastikan data dikirim ke API dalam waktu yang tepat.
        def reset_timer():
            # tiap detect 1 tag rfid message ini ke panggil
            #root.after(0, lambda: messagebox.showinfo("Info", f"Reader mode: {reader_status[reader_id].get('reader_mode', 'N/A')}\nReader status: {reader_status[reader_id]['mode']}\nData reading finished."))

            if reader_status[reader_id]['timer'] is not None:
                # menghentikan timer reader yang sedang berjalan
                # fungsi ini digunakan untuk memastikan bahwa reader
                # tidak membaca terlalu cepat dan memastikan data
                # dikirim ke API dalam waktu yang tepat

                #root.after(0, lambda: messagebox.showinfo("Info", f"Reader mode: {reader_status[reader_id].get('reader_mode', 'N/A')}\nReader status: {reader_status[reader_id]['mode']}\nTimer reset to {reader_status[reader_id]['timer']}"))
                root.after_cancel(reader_status[reader_id]['timer'])

            #root.after(0, lambda: messagebox.showinfo("Info", f"Reader mode: {reader_status[reader_id].get('reader_mode', 'N/A')}\nReader status: {reader_status[reader_id]['mode']}\nTimer reset, waiting for next reading cycle."))
            # Fungsi ini digunakan untuk mengatur timer reader agar membaca tag RFID dalam interval waktu yang ditentukan.
            # Fungsi ini akan dijalankan setiap kali reader selesai membaca dan sebelum mulai membaca lagi.
            # Fungsi ini digunakan untuk memastikan bahwa reader tidak membaca terlalu cepat dan memastikan data dikirim ke API dalam waktu yang tepat.
            # Jika timer reader sudah ada, maka timer tersebut akan dihentikan dan dibuat ulang dengan interval waktu yang baru.
            # Jika timer reader belum ada, maka timer tersebut akan dibuat dengan interval waktu yang ditentukan.
            # Timer reader ini akan memanggil fungsi clear_treeview setelah timer selesai.
            # Fungsi clear_treeview akan menghapus semua data di treeview dan mengirimkan data tag RFID yang unik ke API.

            # root.after(delay, callback, *args):
            reader_status[reader_id]['timer'] = root.after(int(reader.get('reader_interval', 5000)), clear_treeview, reader_id)

        def clear_treeview(reader_id):
            treeview = reader_status[reader_id]['treeview']
            # Deduplicate the stored values
            # Kode ini digunakan untuk menghapus duplikat dari stored_values dan hanya menyimpan tag RFID yang unik.
            # stored_values adalah list yang digunakan untuk menyimpan data tag RFID yang dibaca oleh reader.
            # Fungsi set() digunakan untuk menghapus duplikat dari stored_values dan hanya menyimpan tag RFID yang unik.
            # List comprehension digunakan untuk mengkonversi set menjadi list.
            #unique_tags = [tag for tag in set(reader_status[reader_id]['stored_values'])]

            unique_tags = list(set(reader_status[reader_id]['stored_values']))
            print("Unique tags read:", unique_tags)

            # Send unique tags to API
            # location_update_url = os.getenv('LOCATION_UPDATE')
            middleware_reader_post_url = os.getenv('MIDDLEWARE_READER_POST')
            api_key = os.getenv('API_KEY')
            token = get_saved_token()

            headers = {
                'X-Api-Key': api_key,
                # 'X-Token': token,
                # 'Content-Type': 'application/json'
            }

            for tag in unique_tags:
                cleaned_tag = tag.replace(" ", "")
                librarian_id = reader_status[reader_id].get('librarian_id', 'N/A')
                # reader_id = reader_status[reader_id].get('reader_id', 'N/A')
                reader_room_name = reader_status[reader_id].get('room_name', 'N/A')
                reader_antena = reader_status[reader_id].get('reader_antena', 'N/A')
                reader_angle = reader_status[reader_id].get('reader_angle', 'N/A')
                reader_gate = reader_status[reader_id].get('reader_gate', 'N/A')
                reader_identity = reader_status[reader_id].get('reader_identity', 'N/A')

                payload = {
                    'librarian_id': librarian_id,
                    'reader_id': reader_id,
                    'reader_antena': reader_antena,
                    'reader_angle': reader_angle,
                    'reader_gate': reader_gate,
                    'rfid_tag_number': cleaned_tag,
                    'is_legal_moving': reader_identity
                }

                # looping per baris, terus di post
                try:
                    data = {
                        'room_id': librarian_id,
                        'room_name': reader_room_name,
                        'reader_id': reader_id,
                        'reader_antena': reader_antena,
                        'reader_angle': reader_angle,
                        'reader_gate': reader_gate,
                        'rfid_tag_number': cleaned_tag,
                        'is_legal_moving': reader_identity
                    }

                    print(f"Sending data: {data}")
                    
                    response = requests.post(middleware_reader_post_url, data=data, headers=headers)
                    print(response.text)

                    response.raise_for_status()
                    result = response.json()
                    print(f"Tag {tag} update response: {result}")
                    print(f"Librarian ID: {librarian_id}")  # Print librarian_id

                except requests.exceptions.RequestException as e:
                    print(f"Failed to update tag {tag}: {e} payload: {payload}, headers: {headers}")

            treeview.delete(*treeview.get_children())
            reader_status[reader_id]['stored_values'] = []

        treeview = reader_status[reader_id]['treeview']
        treeview.delete(*treeview.get_children())

        reader_instance = reader_status[reader_id]['instance']
        reader_mode = reader_status[reader_id]['reader_mode']

        reader_family = reader_status[reader_id]['reader_family']

        # root.after(0, lambda: messagebox.showinfo("Info", f"Reader mode: {reader_mode}\nReader status: {reader_status[reader_id]['mode']}\nReader Family: {reader_family}"))

        if reader_mode == 'active' and reader_status[reader_id]['mode'] == "Unread Mode":

            responses: Iterator[Response] = reader_instance.inventory_active_mode()

            try:
                while reader_status[reader_id]['reading_enabled']:
                    for response in responses:
                        tag: bytes = response.data
                        treeview.insert("", "end", values=(hex_readable(tag),))
                        treeview.see(treeview.get_children()[-1])
                        reset_timer()
                        reader_status[reader_id]['stored_values'].append(hex_readable(tag))

                        if not reader_status[reader_id]['reading_enabled']:
                            break

                        print("reader mode: ", reader_mode, "reader status: ", "active")

                        # Print librarian_id
                        print(f"Librarian ID for reader {reader_id}: {reader_status[reader_id].get('librarian_id', 'N/A')}")

            except Exception as e:
                root.after(0, show_error_message, str(e))
                reader_status[reader_id]['reading_enabled'] = False

        elif reader_mode == 'answer' and reader_status[reader_id]['mode'] == "Unread Mode" and reader_status[reader_id]['reader_family'] == 'hw':
            while True:

                try:
                    #print("reader mode: ", reader_mode, "reader status: ", "answer")
                    # tags: Iterator[Tag] = reader_instance.start_inventory_answer_mode(stop_type=StopType.TIME, value=5)  # Set timeout ke 5 detik
                    # tags: Iterator[bytes] = reader_instance.inventory_answer_mode()
                    tags: Iterator[bytes] = reader_instance.start_inventory_answer_mode(stop_type=StopType.TIME, value=5)

                    for tag in tags:
                        if not reader_status[reader_id]['reading_enabled']:
                            break

                        if tag:
                            treeview.insert("", "end", values=(hex_readable(tag),))
                            treeview.see(treeview.get_children()[-1])
                            reset_timer()
                            reader_status[reader_id]['stored_values'].append(hex_readable(tag))

                    if reader_status[reader_id]['mode'] != "Unread Mode":
                        break

                except IndexError:
                    continue
                except Exception as e:
                    root.after(0, show_error_message, str(e))
                    reader_status[reader_id]['reading_enabled'] = False
                    break

        elif reader_mode == 'answer' and reader_status[reader_id]['mode'] == "Unread Mode" and reader_status[reader_id]['reader_family'] == 'rc':
            while True:
                try:
                    # Mulai membaca tag dari reader
                    tags: Iterator[Tag] = reader_instance.start_inventory_answer_mode(stop_type=StopType.TIME, value=5)  # Set timeout ke 5 detik

                    # tags adalah generator, iterasi melaluinya
                    for tag in tags:
                        if not reader_status[reader_id]['reading_enabled']:
                            break

                        # print(f"Tag type: {type(tag)}, Tag content: {tag}")  # Log the tag type and content

                        if tag and hasattr(tag, 'data'):  # Check if tag is not None and has 'data' attribute
                            
                            hex_tag = hex_readable(tag.data)  # Access the 'data' attribute
                            # root.after(0, lambda t=hex_tag: treeview.insert("", "end", values=(t,)))

                            treeview.insert("", "end", values=(hex_tag,))
                            treeview.see(treeview.get_children()[-1])
                            reset_timer()
                            reader_status[reader_id]['stored_values'].append(hex_tag)

                            cleaned_tag = hex_tag.replace(" ", "")
                            print("Unidentified Tag: " + cleaned_tag)

                            tb_master_asets = get_status_aset(cleaned_tag)

                            if tb_master_asets:
                                for tb_master_aset in tb_master_asets:
                                    if isinstance(tb_master_aset, dict):

                                        tipe_moving = tb_master_aset.get('tipe_moving', 'N/A')
                                        print("Tag Identified: " + cleaned_tag + ', tipe_moving: ' + tipe_moving)

                                        if tipe_moving == "0":
                                            # thread = threading.Thread(target=handle_moving_type, args=(reader_instance,))
                                            # reader_instance.stop_inventory_answer_mode()
                                            # threading.Thread(target=handle_moving_type, args=(reader_instance,)).start()

                                            # relay_thread = threading.Thread(target=handle_moving_type, args=(reader_instance,))
                                            # relay_thread.daemon = True
                                            # relay_thread.start()

                                            threading.Thread(target=handle_play_on).start()

                            # reader_instance.stop_inventory_answer_mode()

                            # Panggil untuk menutup relay manual saat mendeteksi tag
                            # close_relay_thread = SetManualRelayThread(reader_instance)
                            # close_relay_thread.release = False  # Set release ke False untuk menutup relay
                            # close_relay_thread.valid_time = 3  # Set valid_time ke 5 detik untuk membuka relay setelah ditutup
                            # close_relay_thread.result_set_manual_relay_signal.connect(__receive_signal_result_set_manual_relay)
                            # close_relay_thread.start()  # Mulai thread untuk menutup relay

                except socket.timeout:
                    # Jika terjadi timeout, log error dan lanjutkan pembacaan
                    #print('Timed out, retrying...')
                    continue  # Coba lagi setelah timeout

                except Exception as e:
                    # Tangani semua error lain
                    root.after(0, show_error_message, str(e))
                    reader_status[reader_id]['reading_enabled'] = False
                    break

    # def __receive_signal_result_set_manual_relay(result):
    #     # Tambahkan logika yang sesuai untuk menangani hasil dari thread
    #     print(f"Relay result: {result}")

    def on_close():
        if messagebox.askokcancel("Exit", "Do you really want to close the application?"):
            root.destroy()
            sys.exit()  # Akhiri program secara eksplisit

    root = tk.Tk() # Membuat window utama
    root.title("List Page")

    # Hubungkan tombol close ke fungsi on_close
    root.protocol("WM_DELETE_WINDOW", on_close)

    tag_readers = get_all_tag_readers()

    if tag_readers:
        # Membuat notebook untuk menampung frame-frame yang akan menampilkan data
        # dari setiap reader. Dan membuat tombol untuk kembali ke halaman dashboard
        notebook = ttk.Notebook(root) # Membuat notebook yang berada di window utama
        dashboard_button = tk.Button(root, text="Back to Dashboard", command=go_to_dashboard)
        dashboard_button.pack(pady= 10)
        dashboard_button.pack(pady=10)

        # Looping untuk setiap reader yang ada di tag_readers
        # dan membuatkan frame untuk menampung data dari setiap reader
        # dan ditambahkan ke notebook agar dapat di navigasi
        for reader in tag_readers:
            if isinstance(reader, dict):

                reader_family = reader.get('reader_family', 'N/A')

                reader_id = reader.get('reader_id', 'N/A')
                reader_name = reader.get('reader_name', 'N/A')
                reader_identity = reader.get('reader_identity', 'N/A')

                # Mengakses librarian_name dari dalam librarian_id
                librarian_info = reader.get('room_id', {})
                librarian_id = librarian_info.get('id', 'N/A')
                reader_room_name = librarian_info.get('ruangan', 'N/A')

                # messagebox.showinfo("Reader Info", f"Reader ID: {reader_id}\nReader Name: {reader_name}\nReader Room: {reader_room_name}\nLibrarian Id: {librarian_id}")

                # Membuat frame untuk menampung data dari reader
                frame = ttk.Frame(notebook) # Membuat frame yang berada di notebook

                # Menambahkan frame ke notebook
                notebook.add(frame, text=reader_name)

                # Mengatur agar frame dapat di resize
                frame.columnconfigure(1, weight=1)

                create_label_and_entry(frame, 0, "Reader ID", reader_id)
                create_label_and_entry(frame, 1, "Ruangan", reader_room_name)
                create_label_and_entry(frame, 2, "Reader Name", reader_name)
                create_label_and_entry(frame, 3, "Serial Number", reader.get('reader_serialnumber', 'N/A'))
                create_label_and_entry(frame, 4, "Type", reader.get('reader_type', 'N/A'))
                
                ip_label, ip_entry = create_label_and_entry(frame, 5, "IP", reader.get('reader_ip', 'N/A'))
                port_label, port_entry = create_label_and_entry(frame, 6, "Port", reader.get('reader_port', 'N/A'))
                serialcom_label, serialcom_entry = create_label_and_entry(frame, 7, "Serial Com", reader.get('reader_com', 'N/A'))
                baudrate_label, baudrate_entry = create_label_and_entry(frame, 8, "Baud Rate", reader.get('reader_baudrate', 'N/A'))
                
                create_label_and_entry(frame, 9, "Power (dbi)", reader.get('reader_power', 'N/A'))
                create_label_and_entry(frame, 10, "Interval (ms)", reader.get('reader_interval', 'N/A'))
                create_label_and_entry(frame, 11, "Reading Method", reader.get('reader_mode', 'N/A'))

                create_label_and_entry(frame, 12, "Reader Family", reader.get('reader_family', 'N/A'))
                create_label_and_entry(frame, 13, "Reader Model", reader.get('reader_model', 'N/A'))
                create_label_and_entry(frame, 14, "Reader Angle", reader.get('reader_angle', 'N/A'))
                create_label_and_entry(frame, 15, "Reader Gate", reader.get('reader_gate', 'N/A'))

                # Membuat list untuk menampung widget yang berhubungan dengan
                # koneksi serial dan tcp agar dapat di hide dan di show
                # berdasarkan pilihan reader type
                serial_widgets = [serialcom_label, serialcom_entry, baudrate_label, baudrate_entry]
                tcp_widgets = [ip_label, ip_entry, port_label, port_entry]

                # Membuat variabel untuk menyimpan pilihan reader type
                type_var = tk.StringVar(value=reader.get('reader_type', 'N/A'))

                # Membuat fungsi untuk menghandle perubahan pilihan reader type
                # dan mengaktifkan atau menonaktifkan widget yang berhubungan dengan serial dan tcp
                type_var.trace_add('write', lambda *args: on_type_change(type_var, serial_widgets, tcp_widgets))

                on_type_change(type_var, serial_widgets, tcp_widgets)  # Initial call to set the correct visibility

                # Initialize status for the reader
                reader_status[reader_id] = {
                    'connected': False,
                    'mode': "Read Mode",
                    'treeview': None,
                    'name': reader_name,
                    'reading_enabled': False,
                    'instance': None,
                    'reader_mode': reader.get('reader_mode', 'N/A'),
                    'thread': None,
                    'timer': None,  # Add timer entry for each reader
                    'stored_values': [],  # Add array to store values
                    'reader_family': reader.get('reader_family', 'N/A'),
                    'librarian_id': librarian_id,
                    'room_name': reader_room_name,
                    'reader_id ': reader.get('reader_id', 'N/A'),
                    'reader_antena': reader.get('reader_antena', 'N/A'),
                    'reader_angle': reader.get('reader_angle', 'N/A'),
                    'reader_gate': reader.get('reader_gate', 'N/A'),
                    'reader_identity': reader_identity
                }

                status_label = tk.Label(frame, text="Reader Disconnected", bg="red", fg="white")
                status_label.grid(row=18, column=0, columnspan=2, pady=10)

                # Tombol untuk menghubungkan dan memutuskan koneksi ke reader
                # dengan nama sesuai dengan pilihan reader type
                connect_button = tk.Button(frame, text=f"Connect {type_var.get()}", width=12, command=lambda r=reader_id, s=status_label: toggle_connection(r, s))
                connect_button.grid(row=17, column=0, padx=10, pady=10, sticky='ew')

                mode_button = tk.Button(frame, text="Read Mode", width=12, state=tk.DISABLED, command=lambda r=reader_id: toggle_mode(r))
                mode_button.grid(row=17, column=1, padx=10, pady=10, sticky='ew')

                treeview = ttk.Treeview(frame, columns=("Tags",), show="headings")
                treeview.heading("Tags", text="Tags")
                treeview.grid(row=19, column=0, columnspan=2, pady=10, sticky='nsew')
                frame.rowconfigure(16, weight=1)
                frame.columnconfigure(1, weight=1)

                reader_status[reader_id] = {
                    'connected': False,
                    'mode': "Read Mode",
                    'treeview': treeview,
                    'name': reader_name,
                    'reading_enabled': False,
                    'instance': None,
                    'reader_mode': reader.get('reader_mode', 'N/A'),
                    'thread': None,
                    'timer': None,
                    'stored_values': [],
                    'librarian_id': librarian_id,
                    'reader_family': reader.get('reader_family', 'N/A'),
                    'room_name': reader_room_name,
                    'reader_id ': reader.get('reader_id ', 'N/A'),
                    'reader_antena': reader.get('reader_antena', 'N/A'),
                    'reader_angle': reader.get('reader_angle', 'N/A'),
                    'reader_gate': reader.get('reader_gate', 'N/A'),
                    'reader_identity': reader_identity
                }

                reader_status[reader_id]['connect_button'] = connect_button
                reader_status[reader_id]['mode_button'] = mode_button

        # Pack the notebook widget so that it expands to fill the available space.
        notebook.pack(expand=1, fill='both')

    else:
        messagebox.showerror("Error", "No tag readers found.")

    root.mainloop()

def __receive_signal_result_set_manual_relay(result):
    # Tambahkan logika yang sesuai untuk menangani hasil dari thread
    print(f"Relay result: {result}")

def handle_moving_type(reader_instance):
    print("handle_moving_type On...")

    # try:
    #     reader_instance.stop_inventory_answer_mode()
    # except AssertionError as e:
    #     print(f"AssertionError: {e}. Kemungkinan respons tidak sesuai dengan yang diharapkan.")
    # except Exception as e:
    #     print(f"Error saat menghentikan mode inventory: {e}")

    close_relay_thread = SetManualRelayThread(reader_instance)
    close_relay_thread.release = False  # Set release ke False untuk menutup relay
    close_relay_thread.valid_time = 0  # Set valid_time ke 10 detik untuk membuka relay setelah ditutup
    close_relay_thread.result_set_manual_relay_signal.connect(__receive_signal_result_set_manual_relay)
    close_relay_thread.start()  # Mulai thread untuk menutup relay

    print("handle_moving_type Off...")

def handle_play_on():
    url_playon = os.getenv('HOST_ALARM_ON')
    print("Requesting: " + url_playon)
    response_relay = requests.post(url_playon)
    print(response_relay)

# if __name__ == "__main__":
#     list_page()
#
# tambahkan fungsi :
# response_set_power: Response = reader.set_power(power)
# print(response_set_power)
# nilai power ambil dari reader_power dan tambahkan setiap reader_power menggunakan id dari reader_id.
# jangan merubah tampilan yang ada. dan jangan mengurangi fungsi / logika yang ada.