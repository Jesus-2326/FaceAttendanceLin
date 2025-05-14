import os
import json
import mysql.connector
from datetime import datetime

# CREDENCIALES MYSQL
DB_CONFIG = {
    "host": "82.180.172.52",
    "user": "u958030263_asisJesus",
    "password": "Beex2025%",
    "database": "u958030263_asistencia"
}

def sync_data():
    carpeta = "asistencias"
    archivos = [f for f in os.listdir(carpeta) if f.endswith(".json")]

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    registros_subidos = 0
    archivos_sincronizados = 0
    errores = []

    for archivo in archivos:
        ruta = os.path.join(carpeta, archivo)

        try:
            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            errores.append(f"Error al leer {archivo}: {e}")
            continue

        if data.get("synced") is True:
            continue  # Ya sincronizado

        fecha = archivo.replace(".json", "")
        registros = data.get("registros", {})

        total_registros = 0
        errores_archivo = 0

        for user_id_str, info in registros.items():
            try:
                user_id = int(user_id_str)
                entrada = info.get("entrada")
                salida = info.get("salida")

                if not entrada:
                    continue  # No se suben registros sin entrada

                total_registros += 1

                # Convertimos a objeto datetime para comparar
                hora_esperada = datetime.strptime("08:00:00", "%H:%M:%S").time()
                max_puntual = datetime.strptime("08:15:00", "%H:%M:%S").time()
                hora_entrada_dt = datetime.strptime(entrada, "%H:%M:%S").time()

                if hora_entrada_dt <= max_puntual:
                    estado = "Puntual"
                else:
                    estado = "Impuntual"

                # Solo actualizamos si los campos en la BD están vacíos
                cursor.execute("""
                    UPDATE asistencias_controladas
                    SET 
                        hora_entrada = IF(hora_entrada IS NULL OR hora_entrada = '', %s, hora_entrada),
                        hora_salida = IF(hora_salida IS NULL OR hora_salida = '', %s, hora_salida),
                        estado = %s
                    WHERE usuario_id = %s AND fecha = %s
                """, (entrada, salida, estado, user_id, fecha))

                registros_subidos += cursor.rowcount

            except Exception as e:
                errores.append(f"Error al actualizar usuario {user_id_str} en {archivo}: {e}")
                errores_archivo += 1

        conn.commit()

        if errores_archivo == 0 and total_registros > 0:
            try:
                data["synced"] = True
                with open(ruta, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                archivos_sincronizados += 1
                print(f"[✔] Sincronizado: {archivo}")
            except Exception as e:
                errores.append(f"Error al marcar como sincronizado {archivo}: {e}")
        else:
            print(f"[⚠️] {archivo} NO se marcó como sincronizado por errores en registros")

    cursor.close()
    conn.close()

    print("\n[📊] RESUMEN DE SINCRONIZACIÓN:")
    print(f" - Registros subidos: {registros_subidos}")
    print(f" - Archivos sincronizados: {archivos_sincronizados}")
    if errores:
        print(f" - ❌ Errores encontrados: {len(errores)}")
        for err in errores:
            print(f"   → {err}")
    else:
        print(" - ✅ Sin errores")

if __name__ == "__main__":
    sync_data()
