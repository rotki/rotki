import process from 'node:process';
import chains from '@test/fixtures/all-evm-chains.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const allEvmChainsHandlers = [
  http.get(`${backendUrl}/api/1/blockchains/evm/all`, () => HttpResponse.json(chains, { status: 200 })),
];
