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
  tradesHandlers,
} from './handlers';

const server = setupServer(
  ...tradesHandlers,
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
