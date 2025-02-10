import tkinter as tk
from tkinter import messagebox
from unittest import result

import requests
import configparser
from dotenv import load_dotenv
import os
import sys

load_dotenv()

def save_token(token, id, email, avatar):
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'token': str(token),
        'id': str(id),
        'email': str(email),
        'avatar': str(avatar)
    }
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def get_saved_token():
    config = configparser.ConfigParser()
    if not os.path.exists('config.ini'):
        return {}
    try:
        config.read('config.ini')
        return {
            'token': config['DEFAULT'].get('token', ''),
            'id': config['DEFAULT'].get('id', ''),
            'email': config['DEFAULT'].get('email', ''),
            'avatar': config['DEFAULT'].get('avatar', '')
        }
    except (configparser.Error, KeyError):
        return {}


def fetch_user_data():
    saved_config = get_saved_token()
    token = saved_config.get('token')
    userid = saved_config.get('id')

    if not token:
        messagebox.showerror("Error", "Token not found. Please login.")
        return None, saved_config

    if not userid:
        messagebox.showerror("Error", "User ID not found. Please check your configuration.")
        return None, saved_config

    dashboard_url = os.getenv('DASHBOARD_URL')
    api_key = os.getenv('API_KEY')
    headers = {'X-API-KEY': api_key, 'X-Token': token}
    params = {'id': userid}

    try:
        response = requests.get(dashboard_url, headers=headers, params=params)
        response.headers["content-type"].strip().startswith("application/json")
        response.raise_for_status()

        #messagebox.showerror("ijin debug bro", response.json())
        result = response.json()
        # messagebox.showerror("Mode Debug", result)
        if not result.get('status'):
            messagebox.showerror("Error", result.get('message', 'Unknown error'))
            return None, saved_config

        user_data = result.get('data', {}).get('user', {})


        if not isinstance(user_data, dict):
            user_data = {}

        return user_data, saved_config
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", str(e))
        import main
        main.form_login()
        return None, saved_config
    except ValueError as e:
        messagebox.showerror("Error", "Invalid response format received from the server.")
        import main
        main.form_login()

def create_label_and_value(frame, row, label_text, value_text, default_value='N/A'):
    label = tk.Label(frame, text=label_text)
    label.grid(row=row, column=0, sticky="w")
    value = tk.Label(frame, text=value_text if value_text else default_value)
    value.grid(row=row, column=1, sticky="w")

def show_dashboard():
    user_data, saved_config = fetch_user_data()

    if user_data is None:
        return

    path_user = os.getenv('PATH_USER', '')

    email = saved_config.get('email', 'N/A')
    userid = saved_config.get('id', 'N/A')
    token = saved_config.get('token', 'N/A')
    avatar = path_user + saved_config.get('avatar', 'N/A')
    api_email = user_data.get('email', 'N/A')
    api_username = user_data.get('username', 'N/A')
    api_avatar = path_user + user_data.get('avatar', 'N/A')

    def logout():
        config = configparser.ConfigParser()
        config.read('config.ini')
        config['DEFAULT']['token'] = ''
        config['DEFAULT']['id'] = ''
        config['DEFAULT']['email'] = ''
        config['DEFAULT']['avatar'] = ''
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        root.destroy()
        import main
        main.form_login()

    def go_to_list():
        root.destroy()
        import list
        list.list_page()

    # Pindahkan fungsi on_close ke sini
    def on_close():
        if messagebox.askokcancel("Exit", "Do you really want to close the application?"):
            root.destroy()
            sys.exit()  # Akhiri program secara eksplisit

    root = tk.Tk()
    root.title("Dashboard")

    # Hubungkan tombol close ke fungsi on_close
    root.protocol("WM_DELETE_WINDOW", on_close)

    session_frame = tk.LabelFrame(root, text="Session Data", padx=10, pady=10)
    session_frame.pack(padx=10, pady=10, fill="both", expand="yes")

    create_label_and_value(session_frame, 0, "Session Email", email)
    create_label_and_value(session_frame, 1, "Session ID", userid)
    create_label_and_value(session_frame, 2, "Session Token", token)
    create_label_and_value(session_frame, 3, "Session Avatar", avatar)

    api_frame = tk.LabelFrame(root, text="API Data", padx=10, pady=10)
    api_frame.pack(padx=10, pady=10, fill="both", expand="yes")

    create_label_and_value(api_frame, 0, "API Email", api_email)
    create_label_and_value(api_frame, 1, "API Username", api_username)
    create_label_and_value(api_frame, 2, "API Avatar", api_avatar)

    logout_button = tk.Button(root, text="Logout", command=logout)
    logout_button.pack(pady=5)

    list_button = tk.Button(root, text="Go to List", command=go_to_list)
    list_button.pack(pady=5)

    # Tambahkan pemanggilan go_to_list() setelah jendela ditampilkan
    # root.after(100, go_to_list)  # Menjadwalkan go_to_list() untuk dipanggil setelah 100ms

    root.mainloop()

# Panggil fungsi show_dashboard untuk menampilkan dashboard
show_dashboard()