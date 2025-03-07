import process from 'node:process';
import { http, HttpResponse } from 'msw';
import nfts from '../../fixtures/nfts.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export const nftsHandlers = [
  http.get(`${backendUrl}/api/1/nfts/balances`, () => HttpResponse.json(nfts, { status: 200 })),
];
