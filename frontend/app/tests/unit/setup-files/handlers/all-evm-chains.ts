import process from 'node:process';
import { HttpResponse, http } from 'msw';
import chains from '../../fixtures/all-evm-chains.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  http.get(`${backendUrl}/api/1/blockchains/evm/all`, () =>
    HttpResponse.json(chains, { status: 200 })),
];
