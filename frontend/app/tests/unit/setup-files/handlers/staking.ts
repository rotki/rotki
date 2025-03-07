import process from 'node:process';
import { http, HttpResponse } from 'msw';
import stakingPerformance from '../../fixtures/staking-performance.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export const stakingHandlers = [
  http.put(`${backendUrl}/api/1/blockchains/eth2/stake/performance`, () =>
    HttpResponse.json(stakingPerformance, { status: 200 })),
];
