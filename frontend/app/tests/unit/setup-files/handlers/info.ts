import { HttpResponse, http } from 'msw';
import info from '../../fixtures/info.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  http.get(`${backendUrl}/api/1/info`, () =>
    HttpResponse.json(info, { status: 200 })),
];
