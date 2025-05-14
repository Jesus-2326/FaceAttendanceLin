import json
import mysql.connector
from datetime import datetime, date
from dotenv import load_dotenv
import os

load_dotenv()

# Conexión a MySQL
conn = mysql.connector.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASS'),
    database=os.getenv('DB_NAME')
)
cursor = conn.cursor(dictionary=True)

# Cargar archivo JSON
with open('/ruta/a/archivo.json', 'r') as f:
    data = json.load(f)

registros = data.get("registros", {})
hoy = date.today()

for usuario_id_str, registro in registros.items():
    usuario_id = int(usuario_id_str)
    entrada = registro.get("entrada")
    salida = registro.get("salida")

    if not entrada:
        continue  # No registrar si no hay hora de entrada

    # Convertir strings a objetos de tiempo
    hora_entrada = datetime.strptime(entrada, '%H:%M:%S').time()
    hora_salida = datetime.strptime(salida, '%H:%M:%S').time() if salida else None

    # Buscar si ya existe registro hoy
    cursor.execute("""
        SELECT id, hora_esperada
        FROM asistencias_controladas
        WHERE usuario_id = %s AND fecha = %s
    """, (usuario_id, hoy))
    asistencia = cursor.fetchone()

    if asistencia:
        # Actualizar entrada/salida
        cursor.execute("""
            UPDATE asistencias_controladas
            SET hora_entrada = %s, hora_salida = %s
            WHERE id = %s
        """, (hora_entrada, hora_salida, asistencia['id']))

        # Evaluar estado
        estado = 'Retardo' if hora_entrada > asistencia['hora_esperada'] else 'Puntual'
        cursor.execute("""
            UPDATE asistencias_controladas
            SET estado = %s
            WHERE id = %s
        """, (estado, asistencia['id']))
    else:
        # Insertar nuevo si no existía
        estado = 'Retardo' if hora_entrada > datetime.strptime('08:00:00', '%H:%M:%S').time() else 'Puntual'
        cursor.execute("""
            INSERT INTO asistencias_controladas (usuario_id, fecha, hora_entrada, hora_salida, hora_esperada, estado)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (usuario_id, hoy, hora_entrada, hora_salida, '08:00:00', estado))

conn.commit()
cursor.close()
conn.close()

print("✔ Registro y actualización de asistencias completo.")