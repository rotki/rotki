import type { MessageHandlerRegistry } from '../interfaces';
import { createDataMigrationHandler, createDbUpgradeHandler } from '../handlers/database-migration';
import { createEventsStatusHandler } from '../handlers/events-status';
import { createEvmAccountsHandler } from '../handlers/evm-accounts';
import { createProgressUpdateHandler } from '../handlers/progress-updates';
import { createTransactionStatusHandler } from '../handlers/transaction-status';
import { SocketMessageType } from '../types/base';

export function createStatusRegistry(
  t: ReturnType<typeof useI18n>['t'],
): Partial<MessageHandlerRegistry> {
  return {
    [SocketMessageType.DATA_MIGRATION_STATUS]: createDataMigrationHandler(),
    [SocketMessageType.DB_UPGRADE_STATUS]: createDbUpgradeHandler(),
    [SocketMessageType.EVM_ACCOUNTS_DETECTION]: createEvmAccountsHandler(),
    [SocketMessageType.HISTORY_EVENTS_STATUS]: createEventsStatusHandler(),
    [SocketMessageType.PROGRESS_UPDATES]: createProgressUpdateHandler(t),
    [SocketMessageType.TRANSACTION_STATUS]: createTransactionStatusHandler(),
  };
}
