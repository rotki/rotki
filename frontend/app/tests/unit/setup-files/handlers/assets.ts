import process from 'node:process';
import { http, HttpResponse } from 'msw';
import assets from '../../fixtures/assets.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export const assetsHandlers = [
  http.post(`${backendUrl}/api/1/assets/all`, () => HttpResponse.json(assets, { status: 200 })),
];
