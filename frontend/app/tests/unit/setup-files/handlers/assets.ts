import process from 'node:process';
import assets from '@test/fixtures/assets.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;
const colibriUrl = `${backendUrl}/colibri`;

export const assetsHandlers = [
  http.post(`${backendUrl}/api/1/assets/all`, () => HttpResponse.json(assets, { status: 200 })),
  // AssetIcon probes colibri on render, and a 404 falls back to the identicon without a request.
  http.head(`${colibriUrl}/assets/icon`, () => new HttpResponse(null, { status: 404 })),
];
