import cv2
import json
import os

# Archivo para guardar los espacios
JSON_FILE = 'espacios.json'

espacios = []
drawing = False
ix, iy = -1, -1

def draw_rectangle(event, x, y, flags, param):
    global ix, iy, drawing, espacios, img, img_copy

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            img_copy = img.copy()
            cv2.rectangle(img_copy, (ix, iy), (x, y), (0, 255, 0), 2)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        w = abs(x - ix)
        h = abs(y - iy)
        x_start = min(ix, x)
        y_start = min(iy, y)
        
        espacio_id = len(espacios) + 1
        espacios.append({
            "id": espacio_id,
            "x": x_start,
            "y": y_start,
            "w": w,
            "h": h
        })
        print(f"Espacio {espacio_id} guardado: x={x_start}, y={y_start}, w={w}, h={h}")
        cv2.rectangle(img, (x_start, y_start), (x_start + w, y_start + h), (0, 255, 0), 2)
        cv2.putText(img, str(espacio_id), (x_start, y_start - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

def main():
    global img, img_copy
    
    # URL de IP Webcam (cambiar por la real o usar 0 para webcam local)
    # Ejemplo: 'http://192.168.1.50:8080/video'
    video_source = input("Ingrese URL de IP Webcam (o presione Enter para webcam local): ")
    if not video_source:
        video_source = 0
    
    cap = cv2.VideoCapture(video_source)
    
    if not cap.isOpened():
        print("Error: No se pudo abrir el video.")
        return

    print("Presione 's' para capturar el frame base y comenzar la calibración.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        cv2.imshow('Captura de Frame Base', frame)
        if cv2.waitKey(1) & 0xFF == ord('s'):
            img = frame.copy()
            img_copy = img.copy()
            # Guardar el frame base para detección futura
            cv2.imwrite('frame_base.jpg', img)
            break
    
    cap.release()
    cv2.destroyWindow('Captura de Frame Base')

    cv2.namedWindow('Calibracion')
    cv2.setMouseCallback('Calibracion', draw_rectangle)

    print("\nInstrucciones:")
    print("- Haga clic y arrastre para dibujar un rectángulo sobre cada espacio.")
    print("- Presione 'r' para reiniciar la selección.")
    print("- Presione 'q' para guardar y salir.")

    while True:
        if drawing:
            cv2.imshow('Calibracion', img_copy)
        else:
            cv2.imshow('Calibracion', img)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            espacios.clear()
            img = cv2.imread('frame_base.jpg')
            print("Selecciones reiniciadas.")
        elif key == ord('q'):
            break

    # Guardar en JSON
    with open(JSON_FILE, 'w') as f:
        json.dump({"espacios": espacios}, f, indent=2)
    
    print(f"\nSe guardaron {len(espacios)} espacios en {JSON_FILE}")
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
