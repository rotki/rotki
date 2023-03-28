import { rest } from 'msw';
import ledgerActions from '../../fixtures/ledger-actions.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  rest.get(`${backendUrl}/api/1/ledgeractions`, (req, res, ctx) =>
    res(ctx.status(200), ctx.json(ledgerActions))
  )
];
