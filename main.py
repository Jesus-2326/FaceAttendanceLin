import tkinter as tk
import cv2 as cv
from PIL import Image, ImageTk
import util
import os
import face_recognition
import subprocess
import datetime
import sys
sys.path.append(r"/home/it/Desktop/FaceAttendence/Silent-Face-Anti-Spoofing-master")
from antispoof_test import test
import pickle
import rawpy
import imageio
import attendance
import json
from sync_to_db import sync_data

class App:
    def __init__(self):
        #Entradas/salidas
        self.hora_inicio_entrada = datetime.time(5, 0)
        self.hora_fin_entrada = datetime.time(12, 0)
        self.hora_inicio_salida = datetime.time(12, 1)
        self.hora_fin_salida = datetime.time(22, 0)

        # Ejecución automatizada para subir la base de datos 
        self.hora_sincronizacion = datetime.time(12, 15)  # Hora en formato HH, MM
        self.ya_sincronizado = False  # Bandera para evitar múltiples ejecuciones en el mismo minuto


        self.main_window = tk.Tk()
        self.main_window.geometry('1200x520+150+100')

        self.login_button_main_window = util.get_button(self.main_window, 'Iniciar Sesion', 'green', self.login)
        self.login_button_main_window.place(x=750, y=300)
        
        self.webcam_label = util.get_img_label(self.main_window)
        self.webcam_label.place(x=10, y=0, width=700, height=500)

        self.add_webcam(self.webcam_label)

        self.db_dir = './db'
        self.convert_jpg_to_pickle()

        #self.db_dir = r'C:\Users\jesus\Desktop\Trabajo\FaceAttendenceSystem\db'
        # Ejecucion de la tarea de subir la db
        self.revisar_sincronizacion()

        if not os.path.exists(self.db_dir):
            os.mkdir(self.db_dir)

        self.log_path = './log.txt'
        # Cargar el diccionario de ID a nombres desde JSON
        try:
            with open("id_to_name.json", "r", encoding="utf-8") as f:
                self.id_to_name = json.load(f)
        except Exception as e:
            print(f"[!] Error cargando id_to_name.json: {e}")
            self.id_to_name = {}



    def add_webcam(self, label):
        if not hasattr(self, "cap") or not self.cap.isOpened():
            self.cap = cv.VideoCapture(0)  # usa 0 si tu cámara principal es /dev/video0

        self._label = label

        # Evitar múltiples ejecuciones del loop
        if not hasattr(self, "webcam_loop_started"):
            self.webcam_loop_started = True
            self.process_webcam()


    def process_webcam(self):
        ret, frame = self.cap.read()
        self.most_recent_capture_arr = frame

        # Dibuja un óvalo donde debe colocarse el rostro
        height, width, _ = frame.shape
        center = (int(width / 2), int(height / 2))
        axes = (70, 100)  # Tamaño del óvalo (ajustable)
        color = (0, 255, 0)  # Verde
        thickness = 2  # Grosor del contorno
        cv.ellipse(frame, center, axes, angle=0, startAngle=0, endAngle=360, color=color, thickness=thickness)

        img_ = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        self.most_recent_capture_pil = Image.fromarray(img_)

        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        self._label.imgtk = imgtk
        self._label.configure(image=imgtk)

        self._label.after(20, self.process_webcam)


    def login(self):
        label = test(
            image=self.most_recent_capture_arr,
            model_dir='/home/it/Desktop/FaceAttendence/Silent-Face-Anti-Spoofing-master/resources/anti_spoof_models',
            device_id=0
        )

        if label == 1:
            id_ = util.recognize(self.most_recent_capture_arr, self.db_dir)
            nombre = self.id_to_name.get(id_)

            if not nombre:
                util.msg_box('Ups...', 'Usuario desconocido. Por favor intentelo de nuevo o registre un nuevo usuario')
                print(f"⚠️  Intento de registro con ID no reconocido: {id_}")
                return

            now = datetime.datetime.now().time()

            # Verificar si está en horario de entrada
            if self.hora_inicio_entrada <= now <= self.hora_fin_entrada:
                tipo = "entrada"
            elif self.hora_inicio_salida <= now <= self.hora_fin_salida:
                tipo = "salida"
            else:
                util.msg_box('Fuera de horario', 'No estás dentro del horario de entrada ni salida permitido.')
                return

            registrado, hora, tipo_detectado = attendance.mark_attendance(id_, nombre, tipo)

            if registrado:
                if tipo_detectado == "entrada":
                    util.msg_box('Bienvenido', f'Bienvenido, {nombre}')
                    print(f"✅ {nombre} registró ENTRADA a las {hora}")
                else:
                    util.msg_box('Adiós', f'Adiós, {nombre}')
                    print(f"✅ {nombre} registró SALIDA a las {hora}")
            else:
                if tipo_detectado == "entrada":
                    util.msg_box('Ya registrado', f'Ya registraste tu ENTRADA, {nombre} a las {hora}')
                    print(f"⚠️ {nombre} ya había registrado ENTRADA a las {hora}")
                else:
                    util.msg_box('Ya registrado', f'Ya registraste tu SALIDA, {nombre} a las {hora}')
                    print(f"⚠️ {nombre} ya había registrado SALIDA a las {hora}")
        else:
            util.msg_box('Error', 'Usuario no real')


    def add_img_to_label(self, label):
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        label.imgtk = imgtk
        label.configure(image=imgtk)

        self.register_new_user_capture = self.most_recent_capture_arr.copy()

    def start(self):
        self.main_window.mainloop()

    def revisar_sincronizacion(self):
        ahora = datetime.datetime.now().time()

        # Si la hora actual coincide (dentro del mismo minuto) y no se ha sincronizado aún
        if ahora.hour == self.hora_sincronizacion.hour and ahora.minute == self.hora_sincronizacion.minute:
            if not self.ya_sincronizado:
                print(f"[⏰] Ejecutando sincronización a las {ahora.strftime('%H:%M')}")
                try:
                    sync_data()
                    self.ya_sincronizado = True
                except Exception as e:
                    print(f"[❌] Error en sincronización automática: {e}")
        else:
            # Resetear bandera si ya pasó la hora
            self.ya_sincronizado = False

        # Vuelve a revisar en 30 segundos
        self.main_window.after(30000, self.revisar_sincronizacion)


    def convert_jpg_to_pickle(self):
        for filename in os.listdir(self.db_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.dng')):  # Soporta .DNG
                name = os.path.splitext(filename)[0]
                pickle_path = os.path.join(self.db_dir, f"{name}.pickle")

                # Si el archivo .pickle ya existe, saltar
                if os.path.exists(pickle_path):
                    continue

                image_path = os.path.join(self.db_dir, filename)

                # Leer DNG con rawpy o JPG con cv2
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


if __name__== '__main__':
    app = App()
    app.start()