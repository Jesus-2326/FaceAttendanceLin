import json
import serial
import time
import adafruit_fingerprint

DB_PATH = "id_huella_a_nombre.json"
uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

# Cargar o crear archivo JSON
try:
    with open(DB_PATH, "r", encoding="utf-8") as f:
        id_to_name = json.load(f)
except:
    id_to_name = {}

def guardar_json():
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(id_to_name, f, indent=4, ensure_ascii=False)

def encontrar_espacio_disponible():
    finger.read_templates()
    ocupados = set(finger.templates or [])
    for i in range(0, finger.library_size, 2):  # de 2 en 2
        if i not in ocupados and i+1 not in ocupados:
            return i
    return None

def enrollar():
    espacio = encontrar_espacio_disponible()
    if espacio is None:
        print("❌ No hay espacio disponible para nuevas huellas.")
        return

    nombre = input("👤 Ingresa el nombre completo de la persona: ").strip()
    for offset in [0, 1]:
        id_guardado = espacio + offset
        print(f"\n📲 Coloca el dedo para registrar huella #{offset+1} (ID {id_guardado})...")
        for intento in range(1, 4):
            while finger.get_image() != adafruit_fingerprint.OK:
                pass
            if finger.image_2_tz(1) != adafruit_fingerprint.OK:
                print("❌ Error al procesar imagen. Intenta nuevamente.")
                continue
            print("✅ Imagen capturada. Retira el dedo...")
            while finger.get_image() != adafruit_fingerprint.NOFINGER:
                pass
            print("📲 Coloca el MISMO dedo de nuevo...")
            while finger.get_image() != adafruit_fingerprint.OK:
                pass
            if finger.image_2_tz(2) != adafruit_fingerprint.OK:
                print("❌ Error en segunda imagen. Intenta de nuevo.")
                continue
            if finger.create_model() != adafruit_fingerprint.OK:
                print("❌ Las huellas no coincidieron. Intenta nuevamente.")
                continue
            if finger.store_model(id_guardado) == adafruit_fingerprint.OK:
                id_to_name[str(id_guardado)] = nombre
                guardar_json()
                print(f"✅ Huella {offset+1} registrada como ID {id_guardado}")
                break
            else:
                print("❌ No se pudo guardar la huella.")
        else:
            print("❌ No se logró registrar la huella tras varios intentos.")
            return

def buscar():
    print("📡 Esperando una huella para buscar coincidencia...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        print("❌ No se pudo procesar la imagen.")
        return
    if finger.finger_search() != adafruit_fingerprint.OK:
        print("❌ No se encontró coincidencia.")
        return
    id_encontrado = str(finger.finger_id)
    nombre = id_to_name.get(id_encontrado, "Desconocido")
    print(f"🔍 Huella encontrada: ID {id_encontrado} - {nombre} (confianza: {finger.confidence})")

def eliminar_individual():
    if not id_to_name:
        print("⚠️  No hay registros para eliminar.")
        return
    print("📋 Huellas registradas:")
    for id_str, nombre in id_to_name.items():
        print(f"  ID {id_str}: {nombre}")
    id_a_borrar = input("🗑️  Ingresa el ID a eliminar: ").strip()
    if id_a_borrar not in id_to_name:
        print("❌ ID no encontrado.")
        return
    confirmar = input(f"¿Eliminar huella ID {id_a_borrar} ({id_to_name[id_a_borrar]})? (s/n): ").lower()
    if confirmar != "s":
        print("❎ Cancelado.")
        return
    if finger.delete_model(int(id_a_borrar)) == adafruit_fingerprint.OK:
        print("✅ Huella eliminada del sensor.")
        del id_to_name[id_a_borrar]
        guardar_json()
    else:
        print("❌ No se pudo eliminar del sensor.")

def eliminar_todas():
    confirmar1 = input("⚠️ ¿Seguro que quieres eliminar TODAS las huellas? (s/n): ").lower()
    if confirmar1 != "s":
        print("❎ Cancelado.")
        return
    confirmar2 = input("🚨 Esta acción es IRREVERSIBLE. ¿Continuar? (s/n): ").lower()
    if confirmar2 != "s":
        print("❎ Cancelado.")
        return
    if finger.empty_library() == adafruit_fingerprint.OK:
        print("🧹 Todas las huellas borradas del sensor.")
        id_to_name.clear()
        guardar_json()
        print("🧾 Archivo de nombres limpio.")
    else:
        print("❌ Error al limpiar la memoria del sensor.")

def mostrar_menu():
    print("\n====== ADMINISTRADOR DE HUELLAS ======")
    print("1) Enrolar persona (2 huellas)")
    print("2) Buscar huella")
    print("3) Eliminar huella individual")
    print("4) Eliminar TODAS las huellas")
    print("q) Salir")
    print("======================================")

def main():
    while True:
        mostrar_menu()
        opcion = input("Elige una opción: ").strip()
        if opcion == "1":
            enrollar()
        elif opcion == "2":
            buscar()
        elif opcion == "3":
            eliminar_individual()
        elif opcion == "4":
            eliminar_todas()
        elif opcion.lower() == "q":
            print("👋 Saliendo...")
            break
        else:
            print("❌ Opción inválida.")

if __name__ == "__main__":
    main()
