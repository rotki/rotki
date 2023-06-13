import { rest } from 'msw';
import historyEventCounterparties from '../../fixtures/history-event-counterparties.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  rest.get(
    `${backendUrl}/api/1/history/events/counterparties`,
    (req, res, ctx) =>
      res(ctx.status(200), ctx.json(historyEventCounterparties))
  )
];
