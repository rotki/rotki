import { HttpResponse, http } from 'msw';
import trades from '../../fixtures/trades.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  http.get(`${backendUrl}/api/1/trades`, () =>
    HttpResponse.json(trades, { status: 200 })),
];
