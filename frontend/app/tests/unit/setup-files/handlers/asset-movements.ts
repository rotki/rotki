import process from 'node:process';
import { HttpResponse, http } from 'msw';
import assetMovements from '../../fixtures/asset-movements.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export const assetMovementHandlers = [
  http.get(`${backendUrl}/api/1/asset_movements`, () => HttpResponse.json(assetMovements, { status: 200 })),
];
