import { setupServer } from 'msw/node';
import assetMovementHandlers from './handlers/asset-movements';
import binanceSavings from './handlers/binance-savings';
import historyEventsHandlers from './handlers/history-events';
import ledgerActionHandlers from './handlers/ledger-actions';
import nfts from './handlers/nfts';
import tradeHandlers from './handlers/trades';
import infoHandlers from './handlers/info';

const server = setupServer(
  ...tradeHandlers,
  ...assetMovementHandlers,
  ...ledgerActionHandlers,
  ...historyEventsHandlers,
  ...nfts,
  ...binanceSavings,
  ...infoHandlers
);

export { server };
