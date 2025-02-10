import tkinter as tk
import requests
import configparser
import os
import threading
from tkinter import ttk, messagebox
from dotenv import load_dotenv
from typing import Iterator
from response import hex_readable, Response
from reader import Reader
from transport import SerialTransport, TcpTransport
from serial.serialutil import PortNotOpenError

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

    def toggle_connection(reader_id):
        reader_name = reader_status[reader_id]['name']
        if reader_status[reader_id]['connected']:
            reader_status[reader_id]['connected'] = False
            reader_status[reader_id]['reading_enabled'] = False
            reader_status[reader_id]['mode'] = "Read Mode"
            connect_button.configure(text="Connect", width=12)
            mode_button.configure(text="Read Mode", state=tk.DISABLED, width=12)
            toggle_treeview(reader_id, mode_button.cget("text"))
            status_label.configure(text="Reader Disconnected", bg="red", fg="white")
            messagebox.showinfo("Info", f"Disconnected from {reader_name}")
        else:
            reader_instance = create_transport(reader_id)
            if reader_instance:
                reader_status[reader_id]['instance'] = reader_instance
                reader_status[reader_id]['connected'] = True
                reader_status[reader_id]['reading_enabled'] = False
                connect_button.configure(text="Disconnect", width=12)
                mode_button.configure(state=tk.NORMAL)
                toggle_treeview(reader_id, mode_button.cget("text"))
                status_label.configure(text="Reader Connected", bg="green", fg="white")
                messagebox.showinfo("Info", f"Connected to {reader_name}")
            else:
                messagebox.showerror("Error", f"Failed to connect to {reader_name}")

    def toggle_mode(reader_id):
        reader_name = reader_status[reader_id]['name']
        reader_instance = reader_status[reader_id]['instance']
        reader_mode = reader_status[reader_id]['reader_mode']
        treeview = reader_status[reader_id]['treeview']

        if reader_status[reader_id]['connected']:
            if reader_status[reader_id]['mode'] == "Read Mode":
                reader_status[reader_id]['mode'] = "Unread Mode"
                reader_status[reader_id]['reading_enabled'] = True
                mode_button.configure(text="Unread Mode", width=12)
                toggle_treeview(reader_id, reader_status[reader_id]['mode'])
                messagebox.showinfo("Info", f"{reader_name} is now in Unread Mode")
                reader_thread = threading.Thread(target=start_reading, args=(reader_id, root))
                reader_thread.daemon = True
                reader_thread.start()
                reader_status[reader_id]['thread'] = reader_thread
            else:
                reader_status[reader_id]['mode'] = "Read Mode"
                reader_status[reader_id]['reading_enabled'] = False
                mode_button.configure(text="Read Mode", width=12)
                treeview.delete(*treeview.get_children())  # Clear the Treeview
                toggle_treeview(reader_id, reader_status[reader_id]['mode'])

    def toggle_treeview(reader_id, mode):
        if mode == "Read Mode":
            reader_status[reader_id]['treeview']["style"] = "enabled.Treeview"
        else:
            reader_status[reader_id]['treeview']["style"] = "disabled.Treeview"

    def create_transport(reader_id):
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
                        transport = TcpTransport(ip_address, int(port))
                        reader_instance = Reader(transport)
                        return reader_instance
                except Exception as e:
                    messagebox.showerror("Error", str(e))
                    return None
        messagebox.showerror("Error", "Reader configuration not found.")
        return None

    def start_reading(reader_id, root):
        def show_error_message(error_message):
            messagebox.showerror("Error", error_message)

        def reset_timer():
            if reader_status[reader_id]['timer'] is not None:
                root.after_cancel(reader_status[reader_id]['timer'])
            reader_status[reader_id]['timer'] = root.after(int(reader.get('reader_interval', 5000)), clear_treeview,
                                                           reader_id)

        def clear_treeview(reader_id):
            treeview = reader_status[reader_id]['treeview']
            # Deduplicate the stored values
            unique_tags = list(set(reader_status[reader_id]['stored_values']))
            print("Unique tags read:", unique_tags)

            # Send unique tags to API
            location_update_url = os.getenv('LOCATION_UPDATE')
            api_key = os.getenv('API_KEY')
            token = get_saved_token()

            headers = {
                'X-Api-Key': api_key,
                'X-Token': token,
                'Content-Type': 'application/json'
            }

            for tag in unique_tags:
                payload = {
                    'Rfid_id': tag,
                    'Librarian_id': reader_status[reader_id].get('librarian_id', 'N/A'),
                    'Location_status': 'updated'  # Example status, you might need to adjust this
                }
                try:
                    response = requests.post(location_update_url, json=payload, headers=headers)
                    response.raise_for_status()
                    result = response.json()
                    print(f"Tag {tag} update response: {result}")
                except requests.exceptions.RequestException as e:
                    print(f"Failed to update tag {tag}: {e}")

            treeview.delete(*treeview.get_children())
            # Clear the stored values in the array
            reader_status[reader_id]['stored_values'] = []

        treeview = reader_status[reader_id]['treeview']
        treeview.delete(*treeview.get_children())
        reader_instance = reader_status[reader_id]['instance']
        reader_mode = reader_status[reader_id]['reader_mode']
        if reader_mode == 'active' and reader_status[reader_id]['mode'] == "Unread Mode":
            responses: Iterator[Response] = reader_instance.inventory_active_mode()
            try:
                while reader_status[reader_id]['reading_enabled']:
                    for response in responses:
                        tag: bytes = response.data
                        treeview.insert("", "end", values=(hex_readable(tag),))
                        treeview.see(treeview.get_children()[-1])  # Scroll to the last entry
                        reset_timer()  # Reset the timer every time a new tag is read
                        # Store the value in the array
                        reader_status[reader_id]['stored_values'].append(hex_readable(tag))
                        if not reader_status[reader_id]['reading_enabled']:
                            break
            except Exception as e:
                root.after(0, show_error_message, str(e))
                reader_status[reader_id]['reading_enabled'] = False
        elif reader_mode == 'answer' and reader_status[reader_id]['mode'] == "Unread Mode":
            tags: Iterator[bytes] = reader_instance.inventory_answer_mode()
            try:
                while reader_status[reader_id]['reading_enabled']:
                    for tag in tags:
                        treeview.insert("", "end", values=(hex_readable(tag),))
                        treeview.see(treeview.get_children()[-1])  # Scroll to the last entry
                        reset_timer()  # Reset the timer every time a new tag is read
                        # Store the value in the array
                        reader_status[reader_id]['stored_values'].append(hex_readable(tag))
                        if not reader_status[reader_id]['reading_enabled']:
                            break
            except Exception as e:
                root.after(0, show_error_message, str(e))
                reader_status[reader_id]['reading_enabled'] = False

    # Main function to show list page remains the same

    # Main function to show list page remains the same

    root = tk.Tk()
    root.title("List Page")

    tag_readers = get_all_tag_readers()

    if tag_readers:
        notebook = ttk.Notebook(root)
        dashboard_button = tk.Button(root, text="Back to Dashboard", command=go_to_dashboard)
        dashboard_button.pack(pady= 10)
        dashboard_button.pack(pady=10)

        for reader in tag_readers:
            if isinstance(reader, dict):
                reader_id = reader.get('reader_id', 'N/A')
                reader_name = reader.get('reader_name', 'N/A')
                frame = ttk.Frame(notebook)
                notebook.add(frame, text=reader_name)

                frame.columnconfigure(1, weight=1)

                create_label_and_entry(frame, 0, "Reader ID", reader_id)
                create_label_and_entry(frame, 1, "Librarian ID", reader.get('librarian_id', 'N/A'))
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

                serial_widgets = [serialcom_label, serialcom_entry, baudrate_label, baudrate_entry]
                tcp_widgets = [ip_label, ip_entry, port_label, port_entry]

                type_var = tk.StringVar(value=reader.get('reader_type', 'N/A'))
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
                    'stored_values': []  # Add array to store values
                }

                connect_button = tk.Button(frame, text="Connect", width=12, command=lambda r=reader_id: toggle_connection(r))
                connect_button.grid(row=12, column=0, padx=10, pady=10, sticky='ew')

                mode_button = tk.Button(frame, text="Read Mode", width=12, state=tk.DISABLED, command=lambda r=reader_id: toggle_mode(r))
                mode_button.grid(row=12, column=1, padx=10, pady=10, sticky='ew')

                status_label = tk.Label(frame, text="Reader Disconnected", bg="red", fg="white")
                status_label.grid(row=13, column=0, columnspan=2, pady=10)

                treeview = ttk.Treeview(frame, columns=("Tags",), show="headings")
                treeview.heading("Tags", text="Tags")
                treeview.grid(row=14, column=0, columnspan=2, pady=10, sticky='nsew')
                frame.rowconfigure(14, weight=1)
                frame.columnconfigure(1, weight=1)
                reader_status[reader_id]['treeview'] = treeview

        notebook.pack(expand=1, fill='both')

    else:
        messagebox.showerror("Error", "No tag readers found.")

    root.mainloop()

# if __name__ == "__main__":
#     list_page()


