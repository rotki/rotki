import process from 'node:process';
import settings from '@test/fixtures/settings.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

/** One fixture, two resources: /settings no longer carries the blob, /settings/frontend serves it. */
const { frontend_settings: frontendSettingsBlob, ...settingsResult } = settings.result;

export const settingsHandlers = [
  http.get(`${backendUrl}/api/1/settings`, () =>
    HttpResponse.json({ ...settings, result: settingsResult }, { status: 200 })),
  http.get(`${backendUrl}/api/1/settings/frontend`, () =>
    HttpResponse.json({ message: '', result: JSON.parse(frontendSettingsBlob) }, { status: 200 })),
  http.put<any, { settings: typeof settingsResult }>(`${backendUrl}/api/1/settings`, async ({ request }) => {
    const params = await request.json();
    const modified = { ...settings, result: { ...settingsResult, ...params.settings } };
    return HttpResponse.json(modified, { status: 200 });
  }),
  // Merged server-side, so there is no stored blob to model here and nothing leaks between specs
  http.patch(`${backendUrl}/api/1/settings/frontend`, () =>
    HttpResponse.json({ message: '', result: true }, { status: 200 })),
];
