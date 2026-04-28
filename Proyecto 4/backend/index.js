const express = require('express');
const axios = require('axios');
const cors = require('cors');

const app = express();
const PORT = 3000;
const VISION_SERVICE_URL = 'http://localhost:5000/api/espacios';

app.use(cors());
app.use(express.json());

// Endpoint para obtener el estado de los espacios
app.get('/api/espacios', async (req, res) => {
    try {
        const response = await axios.get(VISION_SERVICE_URL);
        res.json(response.data);
    } catch (error) {
        console.error('Error al conectar con el servicio de visión:', error.message);
        // Retornar un estado vacío o error controlado
        res.status(500).json({ error: 'No se pudo obtener el estado de los espacios' });
    }
});

app.listen(PORT, () => {
    console.log(`Servidor Backend Node.js corriendo en http://localhost:${PORT}`);
});
