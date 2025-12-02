import process from 'node:process';
import chains from '@test/fixtures/supported-chains.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const supportedChainsHandlers = [
  http.get(`${backendUrl}/api/1/blockchains/supported`, () => HttpResponse.json(chains, { status: 200 })),
];
