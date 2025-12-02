import process from 'node:process';
import binanceSavings from '@test/fixtures/binance-savings.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const binanceSavingsHandlers = [
  http.post(`${backendUrl}/api/1/exchanges/binance/savings`, () => HttpResponse.json(binanceSavings, { status: 200 })),
];
