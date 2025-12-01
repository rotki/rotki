import process from 'node:process';
import historyEventProducts from '@test/fixtures/history-event-products.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const historyEventProductsHandlers = [
  http.get(`${backendUrl}/api/1/history/events/products`, () =>
    HttpResponse.json(historyEventProducts, { status: 200 })),
];
