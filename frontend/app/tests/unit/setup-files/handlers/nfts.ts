import process from 'node:process';
import nfts from '@test/fixtures/nfts.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const nftsHandlers = [
  http.get(`${backendUrl}/api/1/nfts/balances`, () => HttpResponse.json(nfts, { status: 200 })),
];
