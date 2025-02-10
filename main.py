import tkinter as tk
from tkinter import messagebox
import requests
import configparser
from dotenv import load_dotenv
import os

load_dotenv()

def save_token(token, id, email, avatar):
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'Token': str(token),
        'id': str(id),
        'email': str(email),
        'avatar': str(avatar)
    }
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def get_saved_token():
    config = configparser.ConfigParser()
    if not os.path.exists('config.ini'):
        return None
    try:
        config.read('config.ini')
        return {
            'token': config['DEFAULT'].get('token', ''),
            'id': config['DEFAULT'].get('id', ''),
            'email': config['DEFAULT'].get('email', ''),
            'avatar': config['DEFAULT'].get('avatar', '')
        }
    except (configparser.Error, KeyError):
        return None

def activate_session(username, password):
    login_url = os.getenv('LOGIN_URL')
    api_key = os.getenv('API_KEY')
    headers = {'X-API-KEY': api_key}
    data = {'username': username, 'password': password}

    try:
        response = requests.post(login_url, headers=headers, data=data)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", str(e))
        return False

    if result.get('status'):
        token = result.get('token')
        user_data = result.get('data', {})
        id = user_data.get('id')
        email = user_data.get('email')
        avatar = user_data.get('avatar')
        save_token(token, id, email, avatar)
        return True
    else:
        messagebox.showerror("Login Failed", result.get('message', 'Unknown error'))
        return False

def login():
    username = username_entry.get()
    password = password_entry.get()

    if not activate_session(username, password):
        return

    root.destroy()
    import dashboard
    dashboard.show_dashboard()

def form_login():
    global root, username_entry, password_entry
    saved_config = get_saved_token()

    # if saved_config and saved_config.get('token'):
    #     root.destroy()
    #     import dashboard
    #     dashboard.show_dashboard()
    #     return

    root = tk.Tk()
    root.title("Login")

    username_label = tk.Label(root, text="Username:")
    username_label.grid(row=0, column=0, padx=10, pady=5)

    username_entry = tk.Entry(root)
    username_entry.grid(row=0, column=1, padx=10, pady=5)
    username_entry.insert(0, "fatahillah.reza@gmail.com")

    password_label = tk.Label(root, text="Password:")
    password_label.grid(row=1, column=0, padx=10, pady=5)

    password_entry = tk.Entry(root, show="*")
    password_entry.grid(row=1, column=1, padx=10, pady=5)
    password_entry.insert(0, "Developer2023!")

    login_button = tk.Button(root, text="Login", command=login)
    login_button.grid(row=2, column=0, columnspan=2, padx=10, pady=5)

    root.mainloop()

root = tk.Tk()
root.withdraw()

form_login()
