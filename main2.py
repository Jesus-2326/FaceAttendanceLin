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


class App:
    def __init__(self):
        self.main_window = tk.Tk()
        self.main_window.geometry('1200x520+150+100')

        self.login_button_main_window = util.get_button(self.main_window, 'Iniciar Sesion', 'green', self.login)
        self.login_button_main_window.place(x=750, y=300)

        self.register_new_user_main_window = util.get_button(self.main_window, 'Registrar nuevo Usuario', 'gray', self.register_new_user, fg='black')
        self.register_new_user_main_window.place(x=750, y=400)

        self.webcam_label = util.get_img_label(self.main_window)
        self.webcam_label.place(x=10, y=0, width=700, height=500)

        self.add_webcam(self.webcam_label)

        self.db_dir = './db'
        self.convert_jpg_to_pickle()

        #self.db_dir = r'C:\Users\jesus\Desktop\Trabajo\FaceAttendenceSystem\db'

        if not os.path.exists(self.db_dir):
            os.mkdir(self.db_dir)

        self.log_path = './log.txt'


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

        img_ = cv.cvtColor(self.most_recent_capture_arr, cv.COLOR_BGR2RGB)
        self.most_recent_capture_pil = Image.fromarray(img_)

        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        self._label.imgtk = imgtk
        self._label.configure(image=imgtk)

        self._label.after(20, self.process_webcam)

    def login(self):
        #unknown_img_path = './.tmp.jpg'
        #cv.imwrite(unknown_img_path, self.most_recent_capture_arr)
        #output = str(subprocess.check_output(['face_recognition', self.db_dir, unknown_img_path]))
        #name = output.split(',')[1][:-5]

        label = test(image=self.most_recent_capture_arr,
                model_dir = '/home/it/Desktop/FaceAttendence/Silent-Face-Anti-Spoofing-master/resources/anti_spoof_models',
                device_id=0
                ) 
        
        if label == 1:
        
            name = util.recognize(self.most_recent_capture_arr, self.db_dir)


            if name in ['unknown_person', 'no_person_found']:
                util.msg_box('Ups...', 'Usuario desconocido. Por favor intentelo de nuevo o registre un nuevo usuario')
            else:
                with open(self.log_path, 'a') as f:
                    f.write('{},{}\n'.format(name, datetime.datetime.now()))
                    f.close()
                # Registrar asistencia en JSON
                registrado, hora = attendance.mark_attendance(name)
                if registrado:
                    util.msg_box('Bienvenido', 'Bienvenido, {}'.format(name))
                    print(f"✅ {name} registrado en JSON a las {hora}")
                else:
                    util.msg_box('Registrado', 'Ya te habias registrado previamente {}'.format(name))
                    print(f"⚠️  {name} ya había registrado asistencia en JSON a las {hora}")   
        else: 
            util.msg_box('Error', 'Usuario no real')
       # os.remove(unknown_img_path)

    def register_new_user(self):
        self.register_new_user_window = tk.Toplevel(self.main_window)
        self.register_new_user_window.geometry('1200x520+170+120')

        self.accept_button_register_new_user_window = util.get_button(self.register_new_user_window, 'Aceptar', 'green', self.accept_register_new_user)
        self.accept_button_register_new_user_window.place(x=750, y=300)

        self.try_again_button_register_new_user_window = util.get_button(self.register_new_user_window, 'Intentar de nuevo', 'red', self.try_again_register_new_user)
        self.try_again_button_register_new_user_window.place(x=750, y=400)

        self.capture_label = util.get_img_label(self.register_new_user_window)
        self.capture_label.place(x=10, y=0, width=700, height=500)

        self.add_img_to_label(self.capture_label)
        self.entry_text_register_new_user = util.get_entry_text(self.register_new_user_window)  
        self.entry_text_register_new_user.place(x=750, y=150)

        self.text_label_register_new_user = util.get_text_label(self.register_new_user_window,'Ingresa el nombre \ndel nuevo usuario: ')
        self.text_label_register_new_user.place(x=750, y=75)


    def try_again_register_new_user(self):
        self.register_new_user_window.destroy()

    def add_img_to_label(self, label):
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        label.imgtk = imgtk
        label.configure(image=imgtk)

        self.register_new_user_capture = self.most_recent_capture_arr.copy()

    def start(self):
        self.main_window.mainloop()

    def accept_register_new_user(self):
        name = self.entry_text_register_new_user.get(1.0,'end-1c')
        cv.imwrite(os.path.join(self.db_dir,'{}.jpg'.format(name)),self.register_new_user_capture)
        util.msg_box('Registro','Usuario registrado exitosamente')
        self.register_new_user_window.destroy()

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