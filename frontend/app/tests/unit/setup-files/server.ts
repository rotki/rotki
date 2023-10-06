import { setupServer } from 'msw/node';
import assetMovementHandlers from './handlers/asset-movements';
import binanceSavings from './handlers/binance-savings';
import historyEventsHandlers from './handlers/history-events';
import nfts from './handlers/nfts';
import supportedChains from './handlers/supported-chains';
import tradeHandlers from './handlers/trades';
import historyTypeMappingHandlers from './handlers/history-type-mappings';
import historyEventCounterpartiesHandlers from './handlers/history-event-counterparties';
import historyEventProductsHandlers from './handlers/history-event-products';
import infoHandlers from './handlers/info';

const server = setupServer(
  ...tradeHandlers,
  ...assetMovementHandlers,
  ...historyEventsHandlers,
  ...nfts,
  ...binanceSavings,
  ...infoHandlers,
  ...supportedChains,
  ...historyTypeMappingHandlers,
  ...historyEventCounterpartiesHandlers,
  ...historyEventProductsHandlers
);

export { server };
