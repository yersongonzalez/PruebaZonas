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
# Rangos de color amarillo en HSV (ULTRA ESTRICTOS)
LOWER_YELLOW = np.array([20, 150, 150]) 
UPPER_YELLOW = np.array([35, 255, 255])
# Umbral de presencia de color (porcentaje de amarillo dentro del círculo)
COLOR_THRESHOLD = 0.40 

# Configuración de persistencia
PERSISTENCE_THRESHOLD = 8 # Frames para confirmar cambio

# Estado global
estado_espacios = []
historial_conteo = {}

def load_espacios():
    try:
        with open(JSON_FILE, 'r') as f:
            data = json.load(f)
            return data.get('espacios', [])
    except FileNotFoundError:
        print(f"Error: No se encontró {JSON_FILE}")
        return []

def detect_occupancy(video_source):
    global estado_espacios, historial_conteo
    
    espacios = load_espacios()
    if not espacios:
        print("Error: No hay marcadores definidos. Corre calibration.py primero.")
        return

    # Inicializar historial
    for esp in espacios:
        historial_conteo[esp['id']] = {"count": 0, "status_actual": "libre"}

    # Inicializar cámara
    if not video_source:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(video_source)
    
    if not cap.isOpened():
        print(f"Error: No se pudo abrir la fuente de video.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Convertir a HSV para detectar el amarillo
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Crear máscara de amarillo
        mask_yellow = cv2.inRange(hsv, LOWER_YELLOW, UPPER_YELLOW)
        # Limpiar ruido
        kernel = np.ones((5,5), np.uint8)
        mask_yellow = cv2.morphologyEx(mask_yellow, cv2.MORPH_OPEN, kernel)

        nuevos_estados = []
        
        for esp in espacios:
            x, y, r = esp['x'], esp['y'], esp['r']
            esp_id = esp['id']
            
            # Definir el área de búsqueda (un poco más grande que el radio para compensar movimiento)
            search_r = r + 10
            y1, y2 = max(0, y - search_r), min(frame.shape[0], y + search_r)
            x1, x2 = max(0, x - search_r), min(frame.shape[1], x + search_r)
            
            roi_mask = mask_yellow[y1:y2, x1:x2]
            
            # Contar píxeles amarillos visibles
            yellow_pixels = cv2.countNonZero(roi_mask)
            # El área esperada del círculo
            expected_area = np.pi * (r**2)
            
            # Si el porcentaje de amarillo es bajo, el marcador está tapado
            ratio = yellow_pixels / expected_area
            estado_instante = "libre" if ratio > COLOR_THRESHOLD else "ocupado"
            
            # Persistencia
            hist = historial_conteo[esp_id]
            if estado_instante == hist["status_actual"]:
                hist["count"] = 0
            else:
                hist["count"] += 1
                
            if hist["count"] >= PERSISTENCE_THRESHOLD:
                hist["status_actual"] = estado_instante
                hist["count"] = 0
            
            nuevos_estados.append({
                "id": esp_id,
                "estado": hist["status_actual"]
            })

            # Dibujar visualización
            color = (0, 0, 255) if hist["status_actual"] == "ocupado" else (0, 255, 0)
            # Dibujar el círculo de calibración
            cv2.circle(frame, (x, y), r, color, 2)
            # Dibujar el área de búsqueda (línea delgada)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)
            cv2.putText(frame, f"ID {esp_id}: {hist['status_actual']}", (x - 20, y - search_r - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        estado_espacios = nuevos_estados
        
        cv2.imshow('Monitoreo por Marcadores Amarillos', frame)
        cv2.imshow('Deteccion de Color Amarillo', mask_yellow)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

@app.route('/')
def home():
    return "Servicio de Visión funcionando. Usa /api/espacios para ver los datos."

@app.route('/api/espacios', methods=['GET'])
def get_espacios():
    return jsonify({"espacios": estado_espacios})

def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    # Pedir la fuente de video ANTES de iniciar Flask para evitar logs mezclados
    video_source = input("Ingrese URL de IP Webcam para MONITOREO (o Enter para webcam local): ")
    
    # Iniciar Flask en un hilo secundario
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Iniciar detección en el hilo principal
    detect_occupancy(video_source)
