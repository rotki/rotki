import process from 'node:process';
import info from '@test/fixtures/info.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const infoHandlers = [http.get(`${backendUrl}/api/1/info`, () => HttpResponse.json(info, { status: 200 }))];
