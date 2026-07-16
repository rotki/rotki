import process from 'node:process';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const queriedAddressesHandlers = [
  http.get(`${backendUrl}/api/1/queried_addresses`, () => HttpResponse.json({ message: '', result: {} }, { status: 200 })),
];
