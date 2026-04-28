import { Component, ElementRef, OnInit, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import * as cocoSsd from '@tensorflow-models/coco-ssd';
import '@tensorflow/tfjs';

interface Point {
  x: number;
  y: number;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="video-container">
      <video #videoElement autoplay playsinline muted></video>
      <canvas #canvasElement (mousedown)="onMouseDown($event)" (touchstart)="onTouchStart($event)"></canvas>
      
      <div class="status-indicator" [ngClass]="isOccupied ? 'status-occupied' : 'status-free'">
        {{ isOccupied ? 'OCUPADO (MOTO DETECTADA)' : 'DISPONIBLE' }}
      </div>

      <div class="controls">
        <div *ngIf="videoDevices.length > 0" style="display: flex; flex-direction: column; gap: 5px;">
          <label style="font-size: 10px; color: #ccc;">Seleccionar Cámara:</label>
          <select (change)="onDeviceChange($event)" style="padding: 10px; border-radius: 5px; background: rgba(0,0,0,0.7); color: white; border: 1px solid #555;">
            <option value="">-- Automático --</option>
            <option *ngFor="let device of videoDevices" [value]="device.deviceId">
              {{ device.label || 'Cámara ' + device.deviceId.slice(0,5) }}
            </option>
          </select>
        </div>
        <button (click)="clearPerimeter()">Limpiar Perímetro</button>
        <button [class.active]="isDefining" (click)="toggleDefine()">
          {{ isDefining ? 'Finalizar Dibujo' : 'Definir Perímetro' }}
        </button>
      </div>

      <div *ngIf="loading" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 30; background: rgba(0,0,0,0.8); padding: 20px; border-radius: 10px; text-align: center;">
        Cargando modelo IA...
      </div>
    </div>
  `,
  styles: []
})
export class AppComponent implements OnInit, AfterViewInit {
  @ViewChild('videoElement') videoElement!: ElementRef<HTMLVideoElement>;
  @ViewChild('canvasElement') canvasElement!: ElementRef<HTMLCanvasElement>;

  private model: cocoSsd.ObjectDetection | null = null;
  private ctx!: CanvasRenderingContext2D;
  
  loading = true;
  isDefining = false;
  isOccupied = false;
  perimeter: Point[] = [];
  videoDevices: MediaDeviceInfo[] = [];
  selectedDeviceId: string | null = null;
  
  constructor() {}

  async ngOnInit() {
    this.model = await cocoSsd.load({ base: 'mobilenet_v2' });
    this.loading = false;
    this.startDetectionLoop();
  }

  async ngAfterViewInit() {
    await this.listDevices();
    await this.setupCamera();
    this.ctx = this.canvasElement.nativeElement.getContext('2d')!;
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  async listDevices() {
     try {
       // Intentamos pedir permiso. Si falla, al menos enumeramos lo que haya.
       await navigator.mediaDevices.getUserMedia({ video: true }).catch(() => console.log('Permiso denegado inicialmente'));
       const devices = await navigator.mediaDevices.enumerateDevices();
       this.videoDevices = devices.filter(d => d.kind === 'videoinput');
       console.log('Dispositivos encontrados:', this.videoDevices);
     } catch (err) {
       console.error('Error listando dispositivos:', err);
     }
   }

  async onDeviceChange(event: any) {
    this.selectedDeviceId = event.target.value;
    await this.setupCamera();
  }

  async setupCamera() {
    const constraints: any[] = [];

    if (this.selectedDeviceId) {
      constraints.push({
        video: { deviceId: { exact: this.selectedDeviceId }, width: { ideal: 1280 } },
        audio: false
      });
    } else {
      constraints.push(
        { video: { facingMode: 'environment', width: { ideal: 1280 } }, audio: false },
        { video: { width: { ideal: 1280 } }, audio: false },
        { video: true, audio: false }
      );
    }

    let lastError = '';
    for (const constraint of constraints) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia(constraint);
        this.videoElement.nativeElement.srcObject = stream;
        await this.videoElement.nativeElement.play();
        console.log('Cámara conectada con éxito:', constraint);
        return;
      } catch (err: any) {
        lastError = `${err.name}: ${err.message}`;
        console.warn('Fallo con restricción:', constraint, err);
      }
    }

    alert(`Error de Cámara: ${lastError}\n\nSugerencias:\n1. Verifica que DroidCam no esté siendo usada por otra app.\n2. Asegúrate de dar permisos en el navegador.\n3. Si usas Chrome, ve a: chrome://settings/content/camera`);
  }

  resizeCanvas() {
    const video = this.videoElement.nativeElement;
    const canvas = this.canvasElement.nativeElement;
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  toggleDefine() {
    this.isDefining = !this.isDefining;
  }

  clearPerimeter() {
    this.perimeter = [];
    this.isOccupied = false;
  }

  onMouseDown(event: MouseEvent) {
    if (!this.isDefining) return;
    this.addPoint(event.clientX, event.clientY);
  }

  onTouchStart(event: TouchEvent) {
    if (!this.isDefining) return;
    const touch = event.touches[0];
    this.addPoint(touch.clientX, touch.clientY);
  }

  addPoint(x: number, y: number) {
    this.perimeter.push({ x, y });
  }

  async startDetectionLoop() {
    if (this.model && this.videoElement.nativeElement.readyState === 4) {
      try {
        const predictions = await this.model.detect(this.videoElement.nativeElement);
        
        // Filtrar solo motocicletas con un umbral de confianza
        const bikes = predictions.filter(p => p.class === 'motorcycle' && p.score > 0.5);
        
        this.draw(bikes);
        this.checkOccupancy(bikes);
      } catch (err) {
        console.error('Error en la detección:', err);
      }
    }
    // Optimización: Usar setTimeout para controlar los FPS si es necesario, 
    // o mantener requestAnimationFrame para máxima fluidez.
    requestAnimationFrame(() => this.startDetectionLoop());
  }

  checkOccupancy(bikes: cocoSsd.DetectedObject[]) {
    if (this.perimeter.length < 3) {
      this.isOccupied = false;
      return;
    }

    this.isOccupied = bikes.some(bike => {
      const [x, y, width, height] = bike.bbox;
      // Verificamos el centro de la base de la moto (donde toca el suelo)
      const centerX = x + width / 2;
      const centerY = y + height; 
      
      return this.isPointInPolygon({ x: centerX, y: centerY }, this.perimeter);
    });
  }

  // Algoritmo Ray-casting para punto en polígono
  isPointInPolygon(point: Point, polygon: Point[]): boolean {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const xi = polygon[i].x, yi = polygon[i].y;
      const xj = polygon[j].x, yj = polygon[j].y;

      const intersect = ((yi > point.y) !== (yj > point.y))
          && (point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  }

  draw(bikes: cocoSsd.DetectedObject[]) {
    this.ctx.clearRect(0, 0, this.canvasElement.nativeElement.width, this.canvasElement.nativeElement.height);

    // Dibujar perímetro
    if (this.perimeter.length > 0) {
      this.ctx.beginPath();
      this.ctx.moveTo(this.perimeter[0].x, this.perimeter[0].y);
      for (let i = 1; i < this.perimeter.length; i++) {
        this.ctx.lineTo(this.perimeter[i].x, this.perimeter[i].y);
      }
      if (!this.isDefining && this.perimeter.length > 2) {
        this.ctx.closePath();
      }
      this.ctx.strokeStyle = this.isOccupied ? '#ff0000' : '#00ff00';
      this.ctx.lineWidth = 3;
      this.ctx.stroke();
      
      // Relleno semitransparente
      if (!this.isDefining && this.perimeter.length > 2) {
        this.ctx.fillStyle = this.isOccupied ? 'rgba(255, 0, 0, 0.2)' : 'rgba(0, 255, 0, 0.2)';
        this.ctx.fill();
      }

      // Dibujar puntos del perímetro
      this.ctx.fillStyle = 'white';
      this.perimeter.forEach(p => {
        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
        this.ctx.fill();
      });
    }

    // Dibujar detecciones
    bikes.forEach(bike => {
      const [x, y, width, height] = bike.bbox;
      this.ctx.strokeStyle = '#00FFFF';
      this.ctx.lineWidth = 2;
      this.ctx.strokeRect(x, y, width, height);
      
      this.ctx.fillStyle = '#00FFFF';
      this.ctx.fillText(`MOTO: ${(bike.score * 100).toFixed(1)}%`, x, y > 10 ? y - 5 : 10);
    });
  }
}
