import process from 'node:process';
import historyTypeMappings from '@test/fixtures/history-type-mappings.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const historyTypeMappingHandlers = [
  http.get(`${backendUrl}/api/1/history/events/type_mappings`, () =>
    HttpResponse.json(historyTypeMappings, { status: 200 })),
];
