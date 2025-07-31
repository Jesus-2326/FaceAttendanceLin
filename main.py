import tkinter as tk
import cv2 as cv
from PIL import Image, ImageTk
import util
import os
import face_recognition
import subprocess
import datetime
import sys
import json
import pickle
import rawpy
import imageio
import attendance
import threading
from sync_to_db import sync_data
import adafruit_fingerprint
import serial
import time


sys.path.append(r"/home/it/Desktop/FaceAttendanceLin/Silent-Face-Anti-Spoofing-master")
from antispoof_test import test

class App:
    def __init__(self):
        # Entradas/salidas
        self.hora_inicio_entrada = datetime.time(5, 0)
        self.hora_fin_entrada = datetime.time(12, 0)
        self.hora_inicio_salida = datetime.time(12, 1)
        self.hora_fin_salida = datetime.time(22, 0)
        self.hora_sincronizacion = datetime.time(12, 15)
        self.ya_sincronizado = False
        self.lectura_huella_activada = True

        # Huella
        self.db_huella_path = "id_huella_a_nombre.json"
        self.uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)
        self.finger = adafruit_fingerprint.Adafruit_Fingerprint(self.uart)

        try:
            with open(self.db_huella_path, "r", encoding="utf-8") as f:
                self.huella_id_to_name = json.load(f)
        except:
            self.huella_id_to_name = {}

        # Ventana principal fullscreen
        self.main_window = tk.Tk()
        self.main_window.attributes('-fullscreen', True)
        self.main_window.configure(bg="black")

        # Botón de login adaptado a pantalla
        self.login_button_main_window = util.get_button(self.main_window, 'Iniciar Sesión', 'green', self.login)
        self.login_button_main_window.place(relx=0.7, rely=0.65, relwidth=0.25, relheight=0.1)

        # Webcam adaptada a 60% del ancho
        self.webcam_label = util.get_img_label(self.main_window)
        self.webcam_label.place(relx=0.05, rely=0.05, relwidth=0.6, relheight=0.9)

        # Logo
        try:
            logo_path = "Logo.png"
            logo_image = Image.open(logo_path)
            logo_image = logo_image.resize((160, 60), Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_image)
            self.logo_label = tk.Label(self.main_window, image=self.logo_photo, bg="black", cursor="hand2")
            self.logo_label.place(relx=0.75, rely=0.02)
            self.logo_click_count = 0
            self.logo_label.bind("<Button-1>", self.handle_logo_click)
        except Exception as e:
            print(f"[!] No se pudo cargar el logo: {e}")

        self.main_window.bind("<Key>", self.handle_keypress)

        self.add_webcam(self.webcam_label)

        self.db_dir = './db'
        self.convert_jpg_to_pickle()
        self.revisar_sincronizacion()

        if not os.path.exists(self.db_dir):
            os.mkdir(self.db_dir)

        self.log_path = './log.txt'
        try:
            with open("id_to_name.json", "r", encoding="utf-8") as f:
                self.id_to_name = json.load(f)
        except Exception as e:
            print(f"[!] Error cargando id_to_name.json: {e}")
            self.id_to_name = {}

        # Iniciar lectura de huellas en segundo plano
        self.thread_huella = threading.Thread(target=self.leer_huellas, daemon=True)
        self.thread_huella.start()

    def leer_huellas(self):
        while True:
            if self.lectura_huella_activada:
                if self.finger.get_image() == adafruit_fingerprint.OK:
                    if self.finger.image_2_tz(1) == adafruit_fingerprint.OK:
                        if self.finger.finger_search() == adafruit_fingerprint.OK:
                            id_encontrado = str(self.finger.finger_id)
                            nombre = self.huella_id_to_name.get(id_encontrado, "Desconocido")

                            # Buscar el ID real del usuario (id_to_name)
                            id_ = None
                            for key, value in self.id_to_name.items():
                                if value.strip().upper() == nombre.strip().upper():
                                    id_ = key
                                    break

                            if id_ is None:
                                print(f"[❌] Nombre '{nombre}' no encontrado en id_to_name.json, no se registrará asistencia.")
                                return

                            print(f"🆔 Huella detectada: {nombre} (ID {id_encontrado}, confianza {self.finger.confidence})")

                            # Verificar si está en horario válido
                            now = datetime.datetime.now().time()
                            if self.hora_inicio_entrada <= now <= self.hora_fin_entrada:
                                tipo = "entrada"
                            elif self.hora_inicio_salida <= now <= self.hora_fin_salida:
                                tipo = "salida"
                            else:
                                self.main_window.after(0, lambda: util.msg_box('Fuera de horario', 'No estás dentro del horario permitido.'))
                                return

                            # Registrar asistencia
                            registrado, hora, tipo_detectado = attendance.mark_attendance(id_, nombre, tipo)

                            if registrado:
                                msg = 'Bienvenido' if tipo_detectado == "entrada" else 'Adiós'
                                self.main_window.after(0, lambda: util.msg_box(msg, f'{msg}, {nombre}'))
                                print(f"✅ {nombre} registró {tipo_detectado.upper()} a las {hora}")
                            else:
                                self.main_window.after(0, lambda: util.msg_box('Ya registrado', f'Ya registraste tu {tipo_detectado.upper()}, {nombre} a las {hora}'))
                                print(f"⚠️ {nombre} ya había registrado {tipo_detectado.upper()} a las {hora}")

                            time.sleep(2)

            time.sleep(0.2)


    def handle_logo_click(self, event):
        self.logo_click_count += 1
        print(f"[🖱️] Click número: {self.logo_click_count}")
        if self.logo_click_count >= 5:
            print("[🚪] Cierre solicitado por 5 clics en el logo.")
            self.main_window.destroy()

    def handle_keypress(self, event):
        if event.char.lower() == 'q':
            print("[🔴] Cierre solicitado con la tecla 'q'")
            self.main_window.destroy()

    def add_webcam(self, label):
        if not hasattr(self, "cap") or not self.cap.isOpened():
            self.cap = cv.VideoCapture(0)
        self._label = label
        if not hasattr(self, "webcam_loop_started"):
            self.webcam_loop_started = True
            self.process_webcam()

    def process_webcam(self):
        ret, frame = self.cap.read()
        self.most_recent_capture_arr = frame
        height, width, _ = frame.shape
        center = (int(width / 2), int(height / 2))
        axes = (70, 100)
        cv.ellipse(frame, center, axes, angle=0, startAngle=0, endAngle=360, color=(0, 255, 0), thickness=2)
        img_ = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        self.most_recent_capture_pil = Image.fromarray(img_)
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        self._label.imgtk = imgtk
        self._label.configure(image=imgtk)
        self._label.after(20, self.process_webcam)

    def login(self):
        self.lectura_huella_activada = False

        label = test(
            image=self.most_recent_capture_arr,
            model_dir='/home/it/Desktop/FaceAttendanceLin/Silent-Face-Anti-Spoofing-master/resources/anti_spoof_models',
            device_id=0
        )

        if label == 1:
            id_ = util.recognize(self.most_recent_capture_arr, self.db_dir)
            nombre = self.id_to_name.get(id_)

            if not nombre:
                util.msg_box('Ups...', 'Usuario desconocido. Por favor intentelo de nuevo o registre un nuevo usuario')
                print(f"⚠️  Intento de registro con ID no reconocido: {id_}")
                self.lectura_huella_activada = True
                return

            now = datetime.datetime.now().time()
            if self.hora_inicio_entrada <= now <= self.hora_fin_entrada:
                tipo = "entrada"
            elif self.hora_inicio_salida <= now <= self.hora_fin_salida:
                tipo = "salida"
            else:
                util.msg_box('Fuera de horario', 'No estás dentro del horario de entrada ni salida permitido.')
                self.lectura_huella_activada = True
                return

            registrado, hora, tipo_detectado = attendance.mark_attendance(id_, nombre, tipo)

            if registrado:
                msg = 'Bienvenido' if tipo_detectado == "entrada" else 'Adiós'
                util.msg_box(msg, f'{msg}, {nombre}')
                print(f"✅ {nombre} registró {tipo_detectado.upper()} a las {hora}")
            else:
                util.msg_box('Ya registrado', f'Ya registraste tu {tipo_detectado.upper()}, {nombre} a las {hora}')
                print(f"⚠️ {nombre} ya había registrado {tipo_detectado.upper()} a las {hora}")
        else:
            util.msg_box('Error', 'Usuario no real')

        self.lectura_huella_activada = True

    def add_img_to_label(self, label):
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        label.imgtk = imgtk
        label.configure(image=imgtk)
        label.register_new_user_capture = self.most_recent_capture_arr.copy()

    def start(self):
        self.main_window.mainloop()

    def revisar_sincronizacion(self):
        ahora = datetime.datetime.now().time()
        if ahora.hour == self.hora_sincronizacion.hour and ahora.minute == self.hora_sincronizacion.minute:
            if not self.ya_sincronizado:
                print(f"[⏰] Ejecutando sincronización a las {ahora.strftime('%H:%M')}")
                try:
                    sync_data()
                    self.ya_sincronizado = True
                except Exception as e:
                    print(f"[❌] Error en sincronización automática: {e}")
        else:
            self.ya_sincronizado = False
        self.main_window.after(30000, self.revisar_sincronizacion)

    def convert_jpg_to_pickle(self):
        for filename in os.listdir(self.db_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.dng')):
                name = os.path.splitext(filename)[0]
                pickle_path = os.path.join(self.db_dir, f"{name}.pickle")
                if os.path.exists(pickle_path):
                    continue
                image_path = os.path.join(self.db_dir, filename)
                if filename.lower().endswith('.dng'):
                    try:
                        with rawpy.imread(image_path) as raw:
                            img_rgb = raw.postprocess()
                    except Exception as e:
                        print(f"[!] Error al procesar {filename}: {e}")
                        continue
                else:
                    img = cv.imread(image_path)
                    if img is None:
                        print(f"[!] No se pudo leer la imagen {filename}")
                        continue
                    img_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)

                encodings = face_recognition.face_encodings(img_rgb)
                if len(encodings) == 0:
                    print(f"[!] No se detectó rostro en {filename}")
                    continue

                embedding = encodings[0]
                with open(pickle_path, 'wb') as f:
                    pickle.dump(embedding, f)
                print(f"[✓] Embedding generado y guardado para {name}")

if __name__ == '__main__':
    app = App()
    app.start()
