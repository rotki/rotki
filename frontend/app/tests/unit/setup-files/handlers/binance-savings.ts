import { rest } from 'msw';
import binanceSavings from '../../fixtures/binance-savings.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  rest.post(`${backendUrl}/api/1/exchanges/binance/savings`, (req, res, ctx) =>
    res(ctx.status(200), ctx.json(binanceSavings))
  )
];
