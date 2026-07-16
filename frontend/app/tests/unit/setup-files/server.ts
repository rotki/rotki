import { setupServer } from 'msw/node';
import {
  allEvmChainsHandlers,
  assetsHandlers,
  binanceSavingsHandlers,
  historyEventCounterpartiesHandlers,
  historyEventProductsHandlers,
  historyEventsHandlers,
  historyTypeMappingHandlers,
  infoHandlers,
  nftsHandlers,
  premiumHandlers,
  queriedAddressesHandlers,
  settingsHandlers,
  skippedExternalEventsHandlers,
  stakingHandlers,
  supportedChainsHandlers,
  taskSchedulerHandlers,
} from './handlers';

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
