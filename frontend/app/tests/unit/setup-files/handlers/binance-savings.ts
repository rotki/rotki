import process from 'node:process';
import { HttpResponse, http } from 'msw';
import binanceSavings from '../../fixtures/binance-savings.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export const binanceSavingsHandlers = [
  http.post(`${backendUrl}/api/1/exchanges/binance/savings`, () => HttpResponse.json(binanceSavings, { status: 200 })),
];
