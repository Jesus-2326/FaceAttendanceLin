import cv2

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("No se pudo abrir la cámara")
        return

    cv2.namedWindow("Cámara", cv2.WINDOW_NORMAL)
    while True:
        ret, frame = cap.read()
        if not ret:
            print("No se pudo leer el frame")
            break
        cv2.imshow("Cámara", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
