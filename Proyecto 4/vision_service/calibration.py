import cv2
import json
import os

import numpy as np

# Archivo para guardar los espacios
JSON_FILE = 'espacios.json'

# Rangos de color amarillo en HSV (ULTRA ESTRICTOS)
# El amarillo real es muy saturado (S) y brillante (V)
LOWER_YELLOW = np.array([20, 150, 150]) 
UPPER_YELLOW = np.array([35, 255, 255])

def detect_yellow_circles(frame, roi=None):
    """Detecta automáticamente círculos amarillos con validación de color estricta."""
    espacios = []
    
    if roi:
        x_roi, y_roi, w_roi, h_roi = roi
        process_frame = frame[y_roi:y_roi+h_roi, x_roi:x_roi+w_roi]
    else:
        x_roi, y_roi = 0, 0
        process_frame = frame

    hsv_roi = cv2.cvtColor(process_frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_roi, LOWER_YELLOW, UPPER_YELLOW)
    
    # Debug: Mostrar qué se está detectando como amarillo
    cv2.imshow('Mascara de Color (Debug)', mask)
    
    # Limpieza
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    img_result = frame.copy()
    
    print(f"DEBUG: Se encontraron {len(contours)} manchas amarillas potenciales.")
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 40: # Ignorar ruidos pequeños
            continue
            
        (x, y), radius = cv2.minEnclosingCircle(cnt)
        center_in_roi = (int(x), int(y))
        center_global = (int(x) + x_roi, int(y) + y_roi)
        radius = int(radius)
        
        if radius < 5: continue
        
        # 1. Validación de Circularidad (Estricta)
        circle_area = np.pi * (radius ** 2)
        circularity = area / circle_area
        
        # 2. Validación de Color Promedio (Crucial)
        # Creamos una máscara circular para promediar solo el interior del círculo
        circle_mask = np.zeros(mask.shape, dtype=np.uint8)
        cv2.circle(circle_mask, center_in_roi, int(radius*0.8), 255, -1)
        mean_val = cv2.mean(hsv_roi, mask=circle_mask)
        
        # El promedio debe estar en el rango amarillo y ser muy vivo
        is_yellow = (20 <= mean_val[0] <= 40) and (mean_val[1] > 130) and (mean_val[2] > 130)
        
        print(f"DEBUG: Mancha en {center_global} - Circularidad: {circularity:.2f}, HSV Promedio: {mean_val[:3]}")
        
        if circularity > 0.6 and is_yellow:
            espacio_id = len(espacios) + 1
            espacios.append({
                "id": espacio_id,
                "x": center_global[0],
                "y": center_global[1],
                "r": radius
            })
            
            cv2.circle(img_result, center_global, radius, (0, 255, 255), 2)
            cv2.putText(img_result, f"ID:{espacio_id}", (center_global[0] - 10, center_global[1] - radius - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            
    return espacios, img_result

def main():
    video_source = input("Ingrese URL de IP Webcam (o presione Enter para webcam local): ")
    if not video_source:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(video_source)
    
    if not cap.isOpened():
        print(f"Error: No se pudo abrir la fuente de video.")
        return

    print("\n1. Visualización: Presione 's' para CAPTURAR la foto base.")
    
    captured_frame = None
    while True:
        ret, frame = cap.read()
        if not ret: break
        cv2.imshow('Camara - Presione S para capturar', frame)
        if cv2.waitKey(1) & 0xFF == ord('s'):
            captured_frame = frame.copy()
            cv2.imwrite('frame_base.jpg', captured_frame)
            break
    
    cap.release()
    cv2.destroyAllWindows()

    if captured_frame is not None:
        print("\n2. Selección de Área: Dibuje un rectángulo sobre la zona de parqueo y presione ENTER.")
        # cv2.selectROI permite al usuario dibujar un rectángulo
        roi = cv2.selectROI('Seleccione el area de parqueo', captured_frame, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow('Seleccione el area de parqueo')

        if roi[2] > 0 and roi[3] > 0: # Verificar que el ancho y alto sean > 0
            print("\n3. Detectando marcadores amarillos en el área seleccionada...")
            espacios_detectados, img_final = detect_yellow_circles(captured_frame, roi)
            
            print(f"¡Detección completada! Se encontraron {len(espacios_detectados)} marcadores.")
            cv2.imshow('Resultado (Presione Q para guardar, R para cancelar)', img_final)
            
            while True:
                key = cv2.waitKey(0) & 0xFF
                if key == ord('q'):
                    with open(JSON_FILE, 'w') as f:
                        json.dump({"espacios": espacios_detectados}, f, indent=2)
                    print(f"Calibración guardada en {JSON_FILE}")
                    break
                elif key == ord('r'):
                    print("Calibración cancelada.")
                    break
        else:
            print("No se seleccionó un área válida.")

    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
