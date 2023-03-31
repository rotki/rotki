import { rest } from 'msw';
import nfts from '../../fixtures/nfts.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  rest.get(`${backendUrl}/api/1/nfts/balances`, (req, res, ctx) =>
    res(ctx.status(200), ctx.json(nfts))
  )
];
