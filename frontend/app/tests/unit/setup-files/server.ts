import { setupServer } from 'msw/node';
import {
  allEvmChainsHandlers,
  assetMovementHandlers,
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
  ...skippedExternalEventsHandlers,
  ...assetsHandlers,
);

export { server };
