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
  // The endpoint merges server-side and answers `true`, so there is no stored blob to model here
  // and nothing can leak between specs. A spec asserting what was merged asserts on the request.
  http.patch(`${backendUrl}/api/1/settings/frontend`, () =>
    HttpResponse.json({ message: '', result: true }, { status: 200 })),
];
