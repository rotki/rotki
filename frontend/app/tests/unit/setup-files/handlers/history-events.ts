import { rest } from 'msw';
import historyEvents from '../../fixtures/history-events.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  rest.post(`${backendUrl}/api/1/history/events`, (req, res, ctx) =>
    res(ctx.status(200), ctx.json(historyEvents))
  )
];
