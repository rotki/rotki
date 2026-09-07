import { setupServer } from 'msw/node';
import { allEvmChainsHandlers } from './handlers/all-evm-chains';
import { assetsHandlers } from './handlers/assets';
import { binanceSavingsHandlers } from './handlers/binance-savings';
import { historyEventCounterpartiesHandlers } from './handlers/history-event-counterparties';
import { historyEventProductsHandlers } from './handlers/history-event-products';
import { historyEventsHandlers } from './handlers/history-events';
import { historyTypeMappingHandlers } from './handlers/history-type-mappings';
import { infoHandlers } from './handlers/info';
import { nftsHandlers } from './handlers/nfts';
import { premiumHandlers } from './handlers/premium';
import { queriedAddressesHandlers } from './handlers/queried-addresses';
import { settingsHandlers } from './handlers/settings';
import { skippedExternalEventsHandlers } from './handlers/skipped-external-events';
import { stakingHandlers } from './handlers/staking';
import { supportedChainsHandlers } from './handlers/supported-chains';
import { taskSchedulerHandlers } from './handlers/task-scheduler';

const server = setupServer(
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
  ...premiumHandlers,
  ...queriedAddressesHandlers,
  ...settingsHandlers,
  ...skippedExternalEventsHandlers,
  ...assetsHandlers,
  ...taskSchedulerHandlers,
);

export { server };
