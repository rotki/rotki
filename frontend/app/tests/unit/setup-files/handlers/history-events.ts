import process from 'node:process';
import { http, HttpResponse } from 'msw';
import historyEvents from '../../fixtures/history-events.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export const historyEventsHandlers = [
  http.post(`${backendUrl}/api/1/history/events`, () => HttpResponse.json(historyEvents, { status: 200 })),
];
