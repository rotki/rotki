import { rest } from 'msw';
import evmTransactions from '../../fixtures/evm-transactions.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  rest.post(
    `${backendUrl}/api/1/blockchains/evm/transactions`,
    (req, res, ctx) => {
      return res(ctx.status(200), ctx.json(evmTransactions));
    }
  )
];
