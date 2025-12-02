import process from 'node:process';
import stakingPerformance from '@test/fixtures/staking-performance.json';
import { http, HttpResponse } from 'msw';

const backendUrl = process.env.VITE_BACKEND_URL;

export const stakingHandlers = [
  http.put(`${backendUrl}/api/1/blockchains/eth2/stake/performance`, () =>
    HttpResponse.json(stakingPerformance, { status: 200 })),
];
