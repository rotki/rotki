import { setupServer } from 'msw/node';
import { assetMovementHandlers } from './handlers/asset-movements';
import { binanceSavingsHandlers } from './handlers/binance-savings';
import { historyEventsHandlers } from './handlers/history-events';
import { nftsHandlers } from './handlers/nfts';
import { supportedChainsHandlers } from './handlers/supported-chains';
import { allEvmChainsHandlers } from './handlers/all-evm-chains';
import { tradesHandlers } from './handlers/trades';
import { historyTypeMappingHandlers } from './handlers/history-type-mappings';
import { historyEventCounterpartiesHandlers } from './handlers/history-event-counterparties';
import { historyEventProductsHandlers } from './handlers/history-event-products';
import { infoHandlers } from './handlers/info';
import { stakingHandlers } from './handlers/staking';
import { settingsHandlers } from './handlers/settings';

const server = setupServer(
  ...tradesHandlers,
  ...assetMovementHandlers,
  ...historyEventsHandlers,
  ...nftsHandlers,
  ...binanceSavingsHandlers,
  ...infoHandlers,
  ...supportedChainsHandlers,
  ...allEvmChainsHandlers,
  ...historyTypeMappingHandlers,
  ...historyEventCounterpartiesHandlers,
  ...historyEventProductsHandlers,
  ...stakingHandlers,
  ...settingsHandlers,
);

export { server };
