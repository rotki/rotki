import process from 'node:process';
import { HttpResponse, http } from 'msw';
import historyEventCounterparties from '../../fixtures/history-event-counterparties.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export const historyEventCounterpartiesHandlers = [
  http.get(`${backendUrl}/api/1/history/events/counterparties`, () =>
    HttpResponse.json(historyEventCounterparties, { status: 200 })),
];
