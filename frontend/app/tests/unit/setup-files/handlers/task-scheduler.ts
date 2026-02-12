import process from 'node:process';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const taskSchedulerHandlers = [
  http.put(`${backendUrl}/api/1/tasks/scheduler`, () =>
    HttpResponse.json({ result: { enabled: true }, message: '' }, { status: 200 })),
];
