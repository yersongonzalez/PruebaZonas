import cv2
import json
import numpy as np
from flask import Flask, jsonify
from flask_cors import CORS
import threading
import time

app = Flask(__name__)
CORS(app)

# Configuraciones
JSON_FILE = 'espacios.json'
FRAME_BASE_FILE = 'frame_base.jpg'
THRESHOLD_VAL = 45  # Aumentado para ignorar sombras tenues
MIN_PIXELS_RATIO = 0.20  # Aumentado para ser más selectivo
MORP_KERNEL = np.ones((5, 5), np.uint8)

# Estado global de los espacios
estado_espacios = []

def load_espacios():
    try:
        with open(JSON_FILE, 'r') as f:
            data = json.load(f)
            return data.get('espacios', [])
    except FileNotFoundError:
        print(f"Error: No se encontró {JSON_FILE}")
        return []

def detect_occupancy():
    global estado_espacios
    
    espacios = load_espacios()
    if not espacios:
        return

    frame_base = cv2.imread(FRAME_BASE_FILE)
    if frame_base is None:
        print(f"Error: No se pudo cargar {FRAME_BASE_FILE}")
        return

    frame_base_gray = cv2.cvtColor(frame_base, cv2.COLOR_BGR2GRAY)
    frame_base_gray = cv2.GaussianBlur(frame_base_gray, (21, 21), 0)

    # URL de la cámara (debe ser la misma que en la calibración)
    video_source = input("Ingrese URL de IP Webcam para MONITOREO (o Enter para webcam local): ")
    if not video_source:
        video_source = 0
    
    cap = cv2.VideoCapture(video_source)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error al leer de la cámara")
            break

        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_gray = cv2.GaussianBlur(frame_gray, (21, 21), 0)

        # Diferencia absoluta
        diff = cv2.absdiff(frame_base_gray, frame_gray)
        _, thresh = cv2.threshold(diff, THRESHOLD_VAL, 255, cv2.THRESH_BINARY)
        
        # --- MEJORA PARA SOMBRAS ---
        # 1. Eliminar ruido pequeño (sombras tenues)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, MORP_KERNEL)
        # 2. Rellenar huecos en el objeto detectado (el carro)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, MORP_KERNEL)
        # 3. Suavizado adicional
        thresh = cv2.medianBlur(thresh, 5)
        # ---------------------------

        nuevos_estados = []
        
        for esp in espacios:
            x, y, w, h = esp['x'], esp['y'], esp['w'], esp['h']
            roi_diff = thresh[y:y+h, x:x+w]
            
            # Contar píxeles blancos (diferencia)
            count = cv2.countNonZero(roi_diff)
            total_pixels = w * h
            ratio = count / total_pixels
            
            estado = "ocupado" if ratio > MIN_PIXELS_RATIO else "libre"
            nuevos_estados.append({
                "id": esp['id'],
                "estado": estado
            })

            # Dibujar en el frame para visualización
            color = (0, 0, 255) if estado == "ocupado" else (0, 255, 0)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, f"{esp['id']}: {estado}", (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        estado_espacios = nuevos_estados
        
        cv2.imshow('Monitoreo en Tiempo Real', frame)
        cv2.imshow('Mascara de Deteccion (Filtrada)', thresh)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

@app.route('/api/espacios', methods=['GET'])
def get_espacios():
    return jsonify({"espacios": estado_espacios})

def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    # Iniciar detección en un hilo separado para que Flask no bloquee
    # O viceversa. Usaremos el hilo principal para OpenCV y uno secundario para Flask
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    detect_occupancy()
