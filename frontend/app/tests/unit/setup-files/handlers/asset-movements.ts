import { rest } from 'msw';
import assetMovements from '../../fixtures/asset-movements.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  rest.get(`${backendUrl}/api/1/asset_movements`, (req, res, ctx) =>
    res(ctx.status(200), ctx.json(assetMovements))
  )
];
