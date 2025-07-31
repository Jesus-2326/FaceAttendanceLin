import cv2
from pyzbar.pyzbar import decode
import hmac, hashlib, base64
from datetime import datetime

# Tu misma clave secreta que usas en la web
SECRET_KEY = b'secreto_super_seguro'

def verificar_codigo(codigo):
    try:
        partes = codigo.split('|')
        if len(partes) != 5:
            return False, "Formato incorrecto"

        nombre, empresa, motivo, fecha, firma = partes
        datos = f"{nombre}|{empresa}|{motivo}|{fecha}"
        firma_recalculada = base64.urlsafe_b64encode(
            hmac.new(SECRET_KEY, datos.encode(), hashlib.sha256).digest()
        ).decode()

        if firma != firma_recalculada:
            return False, "Firma no válida"

        hoy = datetime.today().strftime("%Y-%m-%d")
        if fecha != hoy:
            return False, f"QR válido solo para {fecha}, hoy es {hoy}"

        return True, f"Bienvenido {nombre} de {empresa} ({motivo})"

    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    cap = cv2.VideoCapture(0)
    print("Escaneando... Presiona 'q' para salir.")

    while True:
        ret, frame = cap.read()
        for qr in decode(frame):
            data = qr.data.decode('utf-8')
            valido, mensaje = verificar_codigo(data)
            print(f"[{'✔️' if valido else '❌'}] {mensaje}")

        cv2.imshow("Lector QR", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
