import process from 'node:process';
import { http, HttpResponse } from 'msw';
import chains from '../../fixtures/all-evm-chains.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export const allEvmChainsHandlers = [
  http.get(`${backendUrl}/api/1/blockchains/evm/all`, () => HttpResponse.json(chains, { status: 200 })),
];
