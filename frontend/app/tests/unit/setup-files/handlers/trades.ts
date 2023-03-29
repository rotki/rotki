import { rest } from 'msw';
import trades from '../../fixtures/trades.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  rest.get(`${backendUrl}/api/1/trades`, (req, res, ctx) =>
    res(ctx.status(200), ctx.json(trades))
  )
];
