import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ParkingService, Espacio } from './services/parking';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class AppComponent implements OnInit, OnDestroy {
  espacios: Espacio[] = [];
  private subscription: Subscription | null = null;

  constructor(private parkingService: ParkingService) {}

  ngOnInit() {
    this.fetchEspacios();
    // Actualizar cada 2 segundos
    this.subscription = interval(2000).subscribe(() => {
      this.fetchEspacios();
    });
  }

  ngOnDestroy() {
    if (this.subscription) {
      this.subscription.unsubscribe();
    }
  }

  fetchEspacios() {
    this.parkingService.getEspacios().subscribe({
      next: (data) => {
        this.espacios = data.espacios;
      },
      error: (err) => {
        console.error('Error fetching parking data', err);
      }
    });
  }
}
