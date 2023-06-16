import { rest } from 'msw';
import info from '../../fixtures/info.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  rest.get(`${backendUrl}/api/1/info`, (req, res, ctx) =>
    res(ctx.status(200), ctx.json(info))
  )
];
