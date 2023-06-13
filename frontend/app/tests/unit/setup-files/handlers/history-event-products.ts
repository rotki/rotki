import { rest } from 'msw';
import historyEventProducts from '../../fixtures/history-event-products.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  rest.get(`${backendUrl}/api/1/history/events/products`, (req, res, ctx) =>
    res(ctx.status(200), ctx.json(historyEventProducts))
  )
];
