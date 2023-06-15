import { rest } from 'msw';
import chains from '../../fixtures/supported-chains.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  rest.get(`${backendUrl}/api/1/blockchains/supported`, (req, res, ctx) =>
    res(ctx.status(200), ctx.json(chains))
  )
];
