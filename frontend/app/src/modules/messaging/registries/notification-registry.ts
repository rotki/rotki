import type { MessageHandlerRegistry } from '../interfaces';
import { createBinancePairsMissingHandler } from '../handlers/binance-pairs-missing';
import { createGnosisPaySessionHandler } from '../handlers/gnosis-pay-session';
import { createLegacyHandler } from '../handlers/legacy';
import { createMissingApiKeyHandler } from '../handlers/missing-api-key';
import { createPremiumStatusHandler } from '../handlers/premium-status';
import { createSnapshotErrorHandler } from '../handlers/snapshot-error';
import { createSolanaTokensHandler } from '../handlers/solana-tokens-migration';
import { SocketMessageType } from '../types/base';

export function createNotificationRegistry(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): Partial<MessageHandlerRegistry> {
  const missingApiKeyHandler = createMissingApiKeyHandler(t, router);
  const binancePairsMissingHandler = createBinancePairsMissingHandler(t, router);

  return {
    [SocketMessageType.BALANCES_SNAPSHOT_ERROR]: createSnapshotErrorHandler(t),
    [SocketMessageType.BINANCE_PAIRS_MISSING]: binancePairsMissingHandler,
    [SocketMessageType.GNOSISPAY_SESSIONKEY_EXPIRED]: createGnosisPaySessionHandler(t, router),
    [SocketMessageType.LEGACY]: createLegacyHandler(t),
    [SocketMessageType.MISSING_API_KEY]: missingApiKeyHandler,
    [SocketMessageType.PREMIUM_STATUS_UPDATE]: createPremiumStatusHandler(t),
    [SocketMessageType.SOLANA_TOKENS_MIGRATION]: createSolanaTokensHandler(t, router),
  };
}
