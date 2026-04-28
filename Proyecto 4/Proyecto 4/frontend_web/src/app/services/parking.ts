import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Espacio {
  id: number;
  estado: 'libre' | 'ocupado';
}

@Injectable({
  providedIn: 'root'
})
export class ParkingService {
  private apiUrl = 'http://localhost:3000/api/espacios';

  constructor(private http: HttpClient) { }

  getEspacios(): Observable<{ espacios: Espacio[] }> {
    return this.http.get<{ espacios: Espacio[] }>(this.apiUrl);
  }
}
