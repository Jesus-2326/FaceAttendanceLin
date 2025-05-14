import json
import os
from datetime import datetime, timedelta

def mark_attendance(user_id, name, tipo):
    fecha = datetime.now().strftime("%Y-%m-%d")
    hora = datetime.now().strftime("%H:%M:%S")

    carpeta = "asistencias"
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    archivo = os.path.join(carpeta, f"{fecha}.json")

    # Cargar asistencias existentes o crear nuevas
    if os.path.exists(archivo):
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
            asistencias = data.get("registros", {})
    else:
        asistencias = {}
        data = {"synced": False, "registros": asistencias}

    if str(user_id) not in asistencias:
        asistencias[str(user_id)] = {
            "nombre": name,
            "entrada": None,
            "salida": None
        }

    registrado = False
    tipo_detectado = tipo

    if tipo == "entrada":
        if asistencias[str(user_id)]["entrada"] is None:
            asistencias[str(user_id)]["entrada"] = hora
            registrado = True
    elif tipo == "salida":
        if asistencias[str(user_id)]["salida"] is None:
            asistencias[str(user_id)]["salida"] = hora
            registrado = True

    # Actualizar estructura y guardar
    data["registros"] = asistencias
    data["synced"] = False  # Siempre marcar como pendiente de sincronizar

    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    eliminar_registros_antiguos(carpeta, dias=7)

    return registrado, hora, tipo_detectado

def eliminar_registros_antiguos(carpeta, dias=7):
    ahora = datetime.now()
    for archivo in os.listdir(carpeta):
        if archivo.endswith(".json"):
            try:
                fecha_str = archivo.replace(".json", "")
                fecha_archivo = datetime.strptime(fecha_str, "%Y-%m-%d")
                if ahora - fecha_archivo > timedelta(days=dias):
                    os.remove(os.path.join(carpeta, archivo))
                    print(f"[🧹] Registro eliminado: {archivo}")
            except Exception as e:
                print(f"[!] Error al procesar archivo {archivo}: {e}")
