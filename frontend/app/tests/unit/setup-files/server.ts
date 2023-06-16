import { setupServer } from 'msw/node';
import assetMovementHandlers from './handlers/asset-movements';
import binanceSavings from './handlers/binance-savings';
import historyEventsHandlers from './handlers/history-events';
import ledgerActionHandlers from './handlers/ledger-actions';
import nfts from './handlers/nfts';
import supportedChains from './handlers/supported-chains';
import tradeHandlers from './handlers/trades';
import historyTypeMappingHandlers from './handlers/history-type-mappings';
import historyEventCounterpartiesHandlers from './handlers/history-event-counterparties';
import historyEventProductsHandlers from './handlers/history-event-products';

const server = setupServer(
  ...tradeHandlers,
  ...assetMovementHandlers,
  ...ledgerActionHandlers,
  ...historyEventsHandlers,
  ...nfts,
  ...supportedChains,
  ...binanceSavings,
  ...historyTypeMappingHandlers,
  ...historyEventCounterpartiesHandlers,
  ...historyEventProductsHandlers
);

export { server };
