import process from 'node:process';
import historyEvents from '@test/fixtures/history-events.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const historyEventsHandlers = [
  http.post(`${backendUrl}/api/1/history/events`, () => HttpResponse.json(historyEvents, { status: 200 })),
];
