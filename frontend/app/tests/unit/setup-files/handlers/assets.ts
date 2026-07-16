import process from 'node:process';
import assets from '@test/fixtures/assets.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;
const colibriUrl = process.env.VITE_COLIBRI_URL;

export const assetsHandlers = [
  http.post(`${backendUrl}/api/1/assets/all`, () => HttpResponse.json(assets, { status: 200 })),
  // AssetIcon probes the colibri icon endpoint on render; answer 404 (no custom icon,
  // identicon fallback) so tests that render icons don't attempt a real connection.
  http.head(`${colibriUrl}/assets/icon`, () => new HttpResponse(null, { status: 404 })),
];
