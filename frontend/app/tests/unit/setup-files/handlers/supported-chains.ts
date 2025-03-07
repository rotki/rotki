import process from 'node:process';
import { http, HttpResponse } from 'msw';
import chains from '../../fixtures/supported-chains.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export const supportedChainsHandlers = [
  http.get(`${backendUrl}/api/1/blockchains/supported`, () => HttpResponse.json(chains, { status: 200 })),
];
