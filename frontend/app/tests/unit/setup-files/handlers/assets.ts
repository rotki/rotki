import process from 'node:process';
import assets from '@test/fixtures/assets.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const assetsHandlers = [
  http.post(`${backendUrl}/api/1/assets/all`, () => HttpResponse.json(assets, { status: 200 })),
];
