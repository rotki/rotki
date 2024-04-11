import { setupServer } from 'msw/node';
import assetMovementHandlers from './handlers/asset-movements';
import binanceSavings from './handlers/binance-savings';
import historyEventsHandlers from './handlers/history-events';
import nfts from './handlers/nfts';
import supportedChains from './handlers/supported-chains';
import allEvmChains from './handlers/all-evm-chains';
import tradeHandlers from './handlers/trades';
import historyTypeMappingHandlers from './handlers/history-type-mappings';
import historyEventCounterpartiesHandlers from './handlers/history-event-counterparties';
import historyEventProductsHandlers from './handlers/history-event-products';
import infoHandlers from './handlers/info';
import stakingHandlers from './handlers/staking';
import settingHandlers from './handlers/settings';

const server = setupServer(
  ...tradeHandlers,
  ...assetMovementHandlers,
  ...historyEventsHandlers,
  ...nfts,
  ...binanceSavings,
  ...infoHandlers,
  ...supportedChains,
  ...allEvmChains,
  ...historyTypeMappingHandlers,
  ...historyEventCounterpartiesHandlers,
  ...historyEventProductsHandlers,
  ...stakingHandlers,
  ...settingHandlers,
);

export { server };
