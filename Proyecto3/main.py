import cv2
import numpy as np
import time
import argparse

class ParkingVisionSystem:
    def __init__(self, video_source=0):
        """
        Sistema de visión para parqueaderos usando visión clásica.
        :param video_source: URL de IP Webcam, ID de cámara local o ruta de video.
        """
        self.cap = cv2.VideoCapture(video_source)
        if not self.cap.isOpened():
            print(f"Error: No se pudo abrir la fuente de video {video_source}")
            exit()

        self.window_name = "Parking Vision System"
        cv2.namedWindow(self.window_name)
        
        # Parámetros de estado
        self.base_frame = None
        self.rows = []  # Estructura para detección automática
        self.manual_bays = [] # Lista de (x, y, w, h) definidos manualmente
        self.drawing = False
        self.ix, self.iy = -1, -1
        
        # Trackbars para ajuste en tiempo real
        cv2.createTrackbar("Umbral Diff", self.window_name, 25, 100, lambda x: None)
        cv2.createTrackbar("Ratio Ocup.", self.window_name, 10, 100, lambda x: None)
        cv2.createTrackbar("Min Area", self.window_name, 500, 5000, lambda x: None)

        # Configurar el callback del mouse
        cv2.setMouseCallback(self.window_name, self.mouse_handler)

        # Rango de color café en HSV (ajustable si es necesario)
        # Nota: El café es un naranja oscuro/bajo en brillo
        self.lower_brown = np.array([0, 20, 20])
        self.upper_brown = np.array([30, 255, 150])

    def mouse_handler(self, event, x, y, flags, param):
        """Maneja los eventos del mouse para dibujo manual."""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.ix, self.iy = x, y

        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            # Calcular dimensiones finales
            x_start, y_start = min(self.ix, x), min(self.iy, y)
            width, height = abs(self.ix - x), abs(self.iy - y)
            
            if width > 5 and height > 5:
                self.manual_bays.append((x_start, y_start, width, height))
                print(f"Bahía manual añadida: {x_start, y_start, width, height}")

    def preprocess_for_separators(self, frame):
        """Usa filtrado de color HSV para detectar los separadores cafés."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_brown, self.upper_brown)
        
        # Limpieza morfológica
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    def detect_layout(self, frame):
        """Detecta automáticamente las filas y columnas de separadores."""
        min_area = cv2.getTrackbarPos("Min Area", self.window_name)
        thresh = self.preprocess_for_separators(frame)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        separators = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = h / float(w)
                if aspect_ratio > 1.5:  # Separadores son verticales
                    separators.append((x, y, w, h))
        
        if len(separators) < 2:
            return False

        # Agrupar por filas (usando el eje Y con un margen de tolerancia)
        separators.sort(key=lambda b: b[1])
        rows_data = []
        if separators:
            current_row = [separators[0]]
            for i in range(1, len(separators)):
                if abs(separators[i][1] - current_row[0][1]) < 60: # Margen de 60px para filas
                    current_row.append(separators[i])
                else:
                    rows_data.append(sorted(current_row, key=lambda b: b[0]))
                    current_row = [separators[i]]
            rows_data.append(sorted(current_row, key=lambda b: b[0]))

        # Construir bahías entre cada par de separadores
        self.rows = []
        for row in rows_data:
            row_bays = []
            for i in range(len(row) - 1):
                sep1 = row[i]
                sep2 = row[i+1]
                
                # Definir la bahía como el espacio entre separadores
                x_start = sep1[0] + sep1[2]
                y_start = sep1[1]
                width = sep2[0] - x_start
                height = sep1[3]
                
                # Filtrar si los separadores están demasiado lejos (no es una bahía)
                if 20 < width < (frame.shape[1] // 3):
                    row_bays.append((x_start, y_start, width, height))
            if row_bays:
                self.rows.append(row_bays)
        
        return len(self.rows) > 0

    def check_occupancy(self, frame):
        """Compara el frame actual con el base para detectar ocupación."""
        # Usar bahías manuales si existen, si no, usar las detectadas automáticamente
        current_bays = []
        if self.manual_bays:
            current_bays = self.manual_bays
        else:
            # Aplanar la lista de filas automáticas
            for row in self.rows:
                current_bays.extend(row)

        if self.base_frame is None or not current_bays:
            return []

        # Obtener valores de los trackbars
        threshold_val = cv2.getTrackbarPos("Umbral Diff", self.window_name)
        min_pixel_ratio = cv2.getTrackbarPos("Ratio Ocup.", self.window_name) / 100.0

        results = []
        # Convertir a escala de grises y aplicar blur para reducir ruido
        gray_current = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (5, 5), 0)
        gray_base = cv2.GaussianBlur(cv2.cvtColor(self.base_frame, cv2.COLOR_BGR2GRAY), (5, 5), 0)

        for i, (x, y, w, h) in enumerate(current_bays):
            # Asegurar que el ROI esté dentro de los límites de la imagen
            h_img, w_img = gray_current.shape
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(w_img, x + w), min(h_img, y + h)
            
            if x2 <= x1 or y2 <= y1:
                continue

            # Extraer ROI
            roi_base = gray_base[y1:y2, x1:x2]
            roi_current = gray_current[y1:y2, x1:x2]
            
            # Diferencia absoluta
            diff = cv2.absdiff(roi_base, roi_current)
            _, diff_thresh = cv2.threshold(diff, threshold_val, 255, cv2.THRESH_BINARY)
            
            # Limpieza de ruido
            kernel = np.ones((3, 3), np.uint8)
            diff_thresh = cv2.morphologyEx(diff_thresh, cv2.MORPH_OPEN, kernel)
            
            # Ratio
            changed_pixels = cv2.countNonZero(diff_thresh)
            total_pixels = (x2 - x1) * (y2 - y1)
            ratio = changed_pixels / total_pixels
            is_occupied = ratio > min_pixel_ratio
            
            results.append({
                'id': i + 1,
                'bbox': (x1, y1, x2 - x1, y2 - y1),
                'occupied': is_occupied,
                'ratio': ratio
            })
        return results

    def draw_results(self, frame, results):
        """Dibuja las bahías, estados y feedback visual."""
        overlay = frame.copy()
        
        # Dibujar rectángulo que se está trazando actualmente
        if self.drawing:
            cv2.rectangle(frame, (self.ix, self.iy), (self.ix, self.iy), (255, 255, 0), 2) # Punto inicial
            # Para mostrar el rectángulo elástico, necesitaríamos guardar las coordenadas actuales del mouse.
            # Por simplicidad, solo mostramos el punto inicial o las bahías ya creadas.

        for res in results:
            x, y, w, h = res['bbox']
            # Verde para libre, Rojo para ocupado (BGR)
            color = (0, 0, 255) if res['occupied'] else (0, 255, 0)
            
            # Dibujar rectángulo semi-transparente
            cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Texto informativo
            label = f"B{res['id']}"
            cv2.putText(frame, label, (x + 5, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Aplicar transparencia al overlay
        alpha = 0.3
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        
        # UI de estado
        cv2.rectangle(frame, (0, 0), (450, 110), (0, 0, 0), -1)
        mode_text = "MODO: MANUAL" if self.manual_bays else "MODO: AUTOMATICO"
        cv2.putText(frame, mode_text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        if self.base_frame is not None:
            cv2.putText(frame, "SISTEMA ACTIVO", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            total_occ = sum(1 for r in results if r['occupied'])
            cv2.putText(frame, f"Ocupados: {total_occ} / {len(results)}", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        else:
            cv2.putText(frame, "ESPERANDO CALIBRACION", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, "Presione 'C' con el parqueadero vacio", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Atajos de teclado
        cv2.putText(frame, "[C] Calibrar | [R] Redetectar Auto | [M] Limpiar Manual | [Q] Salir", 
                    (10, frame.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, "Click y arrastra para demarcar bahias manualmente", 
                    (10, frame.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    def run(self):
        print("Iniciando Parking Vision System...")
        print("Atajos:")
        print("  C: Captura el frame base (debe estar vacío)")
        print("  R: Vuelve a detectar la estructura de separadores")
        print("  Q: Salir")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            # Redimensionar para procesamiento uniforme si es muy grande
            if frame.shape[1] > 1280:
                frame = cv2.resize(frame, (1280, 720))

            # Lógica automática de detección de layout inicial
            if not self.rows:
                self.detect_layout(frame)

            results = self.check_occupancy(frame)
            self.draw_results(frame, results)

            cv2.imshow(self.window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                self.base_frame = frame.copy()
                print("Calibración completada: Frame base guardado.")
            elif key == ord('r'):
                self.rows = []
                self.manual_bays = []
                print("Reiniciando detección de layout (Automático)...")
            elif key == ord('m'):
                self.manual_bays = []
                print("Bahías manuales limpiadas. Regresando a modo automático.")

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sistema de Visión de Parqueadero")
    parser.add_argument("--source", type=str, default="0", help="Fuente de video (ID o URL)")
    args = parser.parse_args()

    # Convertir a entero si es un ID de cámara
    source = int(args.source) if args.source.isdigit() else args.source
    
    system = ParkingVisionSystem(video_source=source)
    system.run()
