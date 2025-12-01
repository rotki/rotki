import process from 'node:process';
import settings from '@test/fixtures/settings.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const settingsHandlers = [
  http.get(`${backendUrl}/api/1/settings`, () => HttpResponse.json(settings, { status: 200 })),
  http.put<any, { settings: (typeof settings)['result'] }>(`${backendUrl}/api/1/settings`, async ({ request }) => {
    const params = await request.json();
    const modified = { ...settings, result: { ...settings.result, ...params.settings } };
    return HttpResponse.json(modified, { status: 200 });
  }),
];
