# Sistema de Detección de Ocupación de Parqueo

Este sistema utiliza visión por computadora para detectar si los espacios de parqueo en una maqueta están libres u ocupados.

## Estructura del Proyecto

- `vision_service/`: Lógica de visión por computadora en Python.
- `backend/`: API en Node.js que sirve los datos a los frontends.
- `frontend_web/`: Aplicación web en Angular.
- `frontend_mobile/`: Aplicación móvil en React Native.

## Requisitos

- Python 3.x
- Node.js & npm
- Celular con la app "IP Webcam" (opcional, o usar webcam local)

## Instrucciones de Ejecución

### 1. Servicio de Visión (Python)
Instala las dependencias:
```bash
cd vision_service
pip install -r requirements.txt
```

**Fase 1: Calibración**
Ejecuta el script para definir los espacios:
```bash
python calibration.py
```
- Ingresa la URL de tu IP Webcam (ej: `http://192.168.1.50:8080/video`).
- Presiona 's' para capturar el frame base.
- Dibuja rectángulos sobre cada espacio con el mouse.
- Presiona 'q' para guardar y salir.

**Fase 2: Monitoreo**
Inicia el servicio de monitoreo y la API:
```bash
python main.py
```
- La API de visión correrá en `http://localhost:5000/api/espacios`.

### 2. Backend (Node.js)
```bash
cd backend
npm install
node index.js
```
- El backend correrá en `http://localhost:3000`.

### 3. Frontend Web (Angular)
```bash
cd frontend_web
npm install
ng serve
```
- Accede a `http://localhost:4200`.

### 4. Frontend Mobile (React Native)
```bash
cd frontend_mobile
# Requiere tener configurado el entorno de React Native
npm install
npx react-native run-android # o run-ios
```

## Lógica de Detección
El sistema compara cada frame actual con un "frame base" (maqueta vacía) capturado durante la calibración. Se calcula la diferencia absoluta de píxeles en escala de grises, se aplica un umbral y si el cambio supera el 15% del área del espacio, se marca como **OCUPADO**.
