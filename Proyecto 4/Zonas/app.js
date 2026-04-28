/**
 * Aplicación de Detección de Bahías de Parqueo
 * Desarrollado por un Ingeniero Experto en Visión por Computadora
 */

class ParkingDetector {
    constructor() {
        this.video = document.getElementById('webcam');
        this.canvas = document.getElementById('output-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.startBtn = document.getElementById('start-btn');
        this.calibrateBtn = document.getElementById('calibrate-btn');
        this.statusText = document.getElementById('status-text');
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.loadingMessage = document.getElementById('loading-message');
        
        this.bayCountEl = document.getElementById('bay-count');
        this.occupiedCountEl = document.getElementById('occupied-count');
        this.availableCountEl = document.getElementById('available-count');

        this.model = null;
        this.bays = []; // Array de objetos { x1, x2, occupied, id }
        this.isCalibrated = false;
        this.isProcessing = false;
        this.fps = 10; // Límite de FPS para procesamiento
        this.lastProcessTime = 0;

        // Configuración de resolución reducida para optimización móvil
        this.processWidth = 640;
        this.processHeight = 480;

        this.init();
    }

    async init() {
        if (window.location.protocol === 'file:') {
            alert('IMPORTANTE: Usa un servidor local (ej: Live Server).');
            this.statusText.textContent = 'Error: file://';
            return;
        }

        console.log('--- Iniciando Depuración de Carga ---');
        try {
            // 1. TensorFlow
            console.log('1. Cargando TensorFlow.js...');
            this.loadingMessage.textContent = 'Cargando TensorFlow.js...';
            if (typeof tf !== 'undefined') {
                tf.env().set('DEBUG', false);
                console.log('TF.js detectado');
            }

            // 2. OpenCV
            console.log('2. Esperando a OpenCV.js...');
            this.loadingMessage.textContent = 'Cargando OpenCV.js (esto puede tardar)...';
            await this.waitForOpenCV();
            console.log('OpenCV.js listo');

            // 3. COCO-SSD
            console.log('3. Cargando COCO-SSD...');
            this.loadingMessage.textContent = 'Cargando modelo COCO-SSD...';
            if (typeof cocoSsd === 'undefined') {
                throw new Error('Librería COCO-SSD no encontrada. Revisa tu conexión.');
            }
            this.model = await cocoSsd.load();
            console.log('COCO-SSD listo');

            this.loadingOverlay.style.display = 'none';
            this.statusText.textContent = 'Listo para iniciar';
            this.startBtn.addEventListener('click', () => this.startCamera());
            this.calibrateBtn.addEventListener('click', () => this.calibrateBays());
        } catch (error) {
            console.error('FALLO EN CARGA:', error);
            this.loadingMessage.textContent = 'Error: ' + error.message;
            this.statusText.textContent = 'Error en inicialización';
        }
    }

    waitForOpenCV() {
        return new Promise((resolve) => {
            // Si ya está inicializado, resolver inmediatamente
            if (typeof cv !== 'undefined' && cv.runtimeInitialized) {
                resolve();
                return;
            }

            // Configurar el callback global que OpenCV.js busca
            window.onOpenCvReady = () => {
                console.log('OpenCV.js is ready (via onOpenCvReady)');
                resolve();
            };

            // Backup: polling si el callback no se dispara
            const check = setInterval(() => {
                if (typeof cv !== 'undefined' && cv.runtimeInitialized) {
                    clearInterval(check);
                    resolve();
                }
            }, 500);
        });
    }

    async startCamera() {
        try {
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: this.processWidth },
                    height: { ideal: this.processHeight }
                },
                audio: false
            };

            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = stream;
            
            this.video.onloadedmetadata = () => {
                this.canvas.width = this.video.videoWidth;
                this.canvas.height = this.video.videoHeight;
                this.processWidth = this.video.videoWidth;
                this.processHeight = this.video.videoHeight;
                
                this.startBtn.disabled = true;
                this.calibrateBtn.disabled = false;
                this.isProcessing = true;
                this.statusText.textContent = 'Cámara activa';
                
                // Primero calibramos automáticamente
                setTimeout(() => this.calibrateBays(), 1000);
                
                this.requestProcessingLoop();
            };
        } catch (error) {
            console.error('Error al acceder a la cámara:', error);
            alert('No se pudo acceder a la cámara. Asegúrate de dar permisos.');
        }
    }

    /**
     * Lógica de OpenCV para detectar líneas y definir bahías
     */
    calibrateBays() {
        if (!this.video.videoWidth) return;

        this.statusText.textContent = 'Calibrando bahías...';
        
        try {
            // 1. Capturar frame actual usando un canvas intermedio
            // cv.imread(video) a veces falla si el video no tiene ID o no es compatible
            let tempCanvas = document.createElement('canvas');
            tempCanvas.width = this.video.videoWidth;
            tempCanvas.height = this.video.videoHeight;
            let tempCtx = tempCanvas.getContext('2d');
            tempCtx.drawImage(this.video, 0, 0, tempCanvas.width, tempCanvas.height);

            let src = cv.imread(tempCanvas);
            let gray = new cv.Mat();
            let edges = new cv.Mat();
            let lines = new cv.Mat();

            // 2. Preprocesamiento
            cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY, 0);
            cv.GaussianBlur(gray, gray, new cv.Size(5, 5), 0, 0, cv.BORDER_DEFAULT);
            
            // 3. Canny Edge Detection
            cv.Canny(gray, edges, 50, 150, 3);

            // 4. HoughLinesP
            cv.HoughLinesP(edges, lines, 1, Math.PI / 180, 50, 80, 30);

            let verticalLinesX = [];
            for (let i = 0; i < lines.rows; ++i) {
                let x1 = lines.data32S[i * 4];
                let y1 = lines.data32S[i * 4 + 1];
                let x2 = lines.data32S[i * 4 + 2];
                let y2 = lines.data32S[i * 4 + 3];

                let angle = Math.abs(Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI);
                // Buscamos líneas que sean predominantemente verticales (75 a 105 grados)
                if (angle > 75 && angle < 105) {
                    verticalLinesX.push((x1 + x2) / 2);
                }
            }

            // 5. Agrupar líneas cercanas
            verticalLinesX.sort((a, b) => a - b);
            let groupedX = [];
            if (verticalLinesX.length > 0) {
                let currentGroupSum = verticalLinesX[0];
                let count = 1;
                for (let i = 1; i < verticalLinesX.length; i++) {
                    if (verticalLinesX[i] - (currentGroupSum / count) < 40) { // Tolerancia aumentada a 40px
                        currentGroupSum += verticalLinesX[i];
                        count++;
                    } else {
                        groupedX.push(currentGroupSum / count);
                        currentGroupSum = verticalLinesX[i];
                        count = 1;
                    }
                }
                groupedX.push(currentGroupSum / count);
            }

            if (groupedX.length < 2) {
                this.statusText.textContent = 'No se detectaron suficientes líneas. Reintenta.';
                console.warn('Líneas detectadas insuficientes:', groupedX.length);
            } else {
                // 6. Crear bahías
                this.bays = [];
                for (let i = 0; i < groupedX.length - 1; i++) {
                    this.bays.push({
                        id: i + 1,
                        x1: groupedX[i],
                        x2: groupedX[i+1],
                        occupied: false
                    });
                }
                this.bayCountEl.textContent = this.bays.length;
                this.isCalibrated = true;
                this.statusText.textContent = 'Monitoreando...';
            }

            // Limpiar memoria
            src.delete(); gray.delete(); edges.delete(); lines.delete();
        } catch (e) {
            console.error('Error en calibración:', e);
            this.statusText.textContent = 'Error en OpenCV';
        }
    }

    requestProcessingLoop() {
        const now = Date.now();
        if (now - this.lastProcessTime >= 1000 / this.fps) {
            this.processFrame();
            this.lastProcessTime = now;
        }
        if (this.isProcessing) {
            requestAnimationFrame(() => this.requestProcessingLoop());
        }
    }

    async processFrame() {
        if (!this.isCalibrated) return;

        // 1. Detectar motocicletas con TF.js
        const predictions = await this.model.detect(this.video);
        const motorcycles = predictions.filter(p => p.class === 'motorcycle' && p.score > 0.5);

        // 2. Reiniciar estado de bahías
        this.bays.forEach(bay => bay.occupied = false);

        // 3. Lógica de intersección
        motorcycles.forEach(mc => {
            const [mx, my, mw, mh] = mc.bbox;
            const mcCenterX = mx + mw / 2;
            
            // Verificamos si el centro de la motocicleta está dentro de los límites X de la bahía
            // Añadimos un pequeño margen de tolerancia
            this.bays.forEach(bay => {
                const margin = 10;
                if (mcCenterX >= (bay.x1 - margin) && mcCenterX <= (bay.x2 + margin)) {
                    bay.occupied = true;
                }
            });
        });

        this.drawResults(motorcycles);
        this.updateStats();
    }

    drawResults(motorcycles) {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Dibujar Bahías
        this.bays.forEach(bay => {
            const color = bay.occupied ? 'rgba(217, 48, 37, 0.5)' : 'rgba(30, 142, 62, 0.5)';
            const borderColor = bay.occupied ? '#d93025' : '#1e8e3e';
            
            // Área de la bahía
            this.ctx.fillStyle = color;
            this.ctx.fillRect(bay.x1, 0, bay.x2 - bay.x1, this.canvas.height);
            
            // Líneas delimitadoras
            this.ctx.strokeStyle = borderColor;
            this.ctx.lineWidth = 4;
            this.ctx.beginPath();
            this.ctx.moveTo(bay.x1, 0);
            this.ctx.lineTo(bay.x1, this.canvas.height);
            this.ctx.moveTo(bay.x2, 0);
            this.ctx.lineTo(bay.x2, this.canvas.height);
            this.ctx.stroke();

            // Número de bahía
            this.ctx.fillStyle = 'white';
            this.ctx.font = 'bold 24px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.fillText(bay.id, bay.x1 + (bay.x2 - bay.x1) / 2, 40);
            
            const statusLabel = bay.occupied ? 'OCUPADO' : 'LIBRE';
            this.ctx.font = 'bold 14px Arial';
            this.ctx.fillText(statusLabel, bay.x1 + (bay.x2 - bay.x1) / 2, 70);
        });

        // Dibujar detecciones de motocicletas (opcional, para feedback)
        motorcycles.forEach(mc => {
            const [x, y, w, h] = mc.bbox;
            this.ctx.strokeStyle = '#fbbc04';
            this.ctx.lineWidth = 2;
            this.ctx.strokeRect(x, y, w, h);
            
            this.ctx.fillStyle = '#fbbc04';
            this.ctx.font = '12px Arial';
            this.ctx.fillText(`Moto ${(mc.score * 100).toFixed(0)}%`, x + w/2, y - 5);
        });
    }

    updateStats() {
        const occupied = this.bays.filter(b => b.occupied).length;
        const available = this.bays.length - occupied;
        
        this.occupiedCountEl.textContent = occupied;
        this.availableCountEl.textContent = available;
    }
}

// Inicializar la aplicación
window.addEventListener('DOMContentLoaded', () => {
    new ParkingDetector();
});
