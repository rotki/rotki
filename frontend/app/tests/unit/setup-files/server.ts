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
  settingsHandlers,
  skippedExternalEventsHandlers,
  stakingHandlers,
  supportedChainsHandlers,
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
  ...settingsHandlers,
  ...skippedExternalEventsHandlers,
  ...assetsHandlers,
);

export { server };
