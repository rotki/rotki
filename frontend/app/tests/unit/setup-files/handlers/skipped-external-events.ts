import process from 'node:process';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const skippedExternalEventsHandlers = [
  http.get(`${backendUrl}/api/1/history/skipped_external_events`, () => HttpResponse.json({
    result: {
      locations: {},
      total: 0,
    },
    message: '',
  }, { status: 200 })),
];
