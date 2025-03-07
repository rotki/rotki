import process from 'node:process';
import { http, HttpResponse } from 'msw';
import historyEventProducts from '../../fixtures/history-event-products.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export const historyEventProductsHandlers = [
  http.get(`${backendUrl}/api/1/history/events/products`, () =>
    HttpResponse.json(historyEventProducts, { status: 200 })),
];
