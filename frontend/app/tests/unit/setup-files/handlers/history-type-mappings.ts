import { rest } from 'msw';
import historyTypeMappings from '../../fixtures/history-type-mappings.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  rest.get(
    `${backendUrl}/api/1/history/events/type_mappings`,
    (req, res, ctx) => res(ctx.status(200), ctx.json(historyTypeMappings))
  )
];
