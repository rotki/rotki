import process from 'node:process';
import settings from '@test/fixtures/settings.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

/** The fixture predates the split, so the blob is carved out of it for /settings/frontend. */
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
  http.patch(`${backendUrl}/api/1/settings/frontend`, () =>
    HttpResponse.json({ message: '', result: true }, { status: 200 })),
];
