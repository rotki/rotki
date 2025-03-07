import process from 'node:process';
import { http, HttpResponse } from 'msw';
import trades from '../../fixtures/trades.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export const tradesHandlers = [
  http.get(`${backendUrl}/api/1/trades`, () => HttpResponse.json(trades, { status: 200 })),
];
