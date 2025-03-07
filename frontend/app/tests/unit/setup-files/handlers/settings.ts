import process from 'node:process';
import { http, HttpResponse } from 'msw';
import settings from '../../fixtures/settings.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export const settingsHandlers = [
  http.get(`${backendUrl}/api/1/settings`, () => HttpResponse.json(settings, { status: 200 })),
  http.put<any, { settings: (typeof settings)['result'] }>(`${backendUrl}/api/1/settings`, async ({ request }) => {
    const params = await request.json();
    const modified = { ...settings, result: { ...settings.result, ...params.settings } };
    return HttpResponse.json(modified, { status: 200 });
  }),
];
