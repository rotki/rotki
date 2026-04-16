import type { MessageHandlerRegistry } from '../interfaces';
import { createNegativeBalanceDetectedHandler } from '@/modules/history/balances/negative-balance-detected-handler';
import { createEventsStatusHandler } from '@/modules/history/events-status-handler';
import { createTransactionStatusHandler } from '@/modules/history/transaction-status-handler';
import { createDataMigrationHandler, createDbUpgradeHandler } from '../handlers/database-migration';
import { createEvmAccountsHandler } from '../handlers/evm-accounts';
import { createInternalTxFixedHandler } from '../handlers/internal-tx-fixed';
import { createProgressUpdateHandler } from '../handlers/progress-updates';
import { SocketMessageType } from '../types/base';

export function createStatusRegistry(
  t: ReturnType<typeof useI18n>['t'],
): Partial<MessageHandlerRegistry> {
  return {
    [SocketMessageType.DATA_MIGRATION_STATUS]: createDataMigrationHandler(),
    [SocketMessageType.DB_UPGRADE_STATUS]: createDbUpgradeHandler(),
    [SocketMessageType.EVM_ACCOUNTS_DETECTION]: createEvmAccountsHandler(),
    [SocketMessageType.HISTORY_EVENTS_STATUS]: createEventsStatusHandler(),
    [SocketMessageType.INTERNAL_TX_FIXED]: createInternalTxFixedHandler(),
    [SocketMessageType.NEGATIVE_BALANCE_DETECTED]: createNegativeBalanceDetectedHandler(),
    [SocketMessageType.PROGRESS_UPDATES]: createProgressUpdateHandler(t),
    [SocketMessageType.TRANSACTION_STATUS]: createTransactionStatusHandler(),
  };
}
