import process from 'node:process';
import historyEventCounterparties from '@test/fixtures/history-event-counterparties.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const historyEventCounterpartiesHandlers = [
  http.get(`${backendUrl}/api/1/history/events/counterparties`, () =>
    HttpResponse.json(historyEventCounterparties, { status: 200 })),
];
