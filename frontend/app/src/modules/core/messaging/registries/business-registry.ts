import type { MessageHandlerRegistry } from '../interfaces';
import { createExchangeUnknownAssetHandler } from '@/modules/assets/admin/missing-mappings/exchange-unknown-asset-handler';
import { createNewTokenDetectedHandler } from '@/modules/assets/detection/new-token-detected-handler';
import { createAccountingRuleConflictHandler } from '../handlers/accounting-rule-conflict';
import { createCalendarReminderHandler } from '../handlers/calendar-reminder';
import { createDbUploadProgressHandler, createDbUploadResultHandler } from '../handlers/database-upload';
import { createHistoricalBalanceProcessingCompletedHandler } from '../handlers/historical-balance-processing-completed';
import { createRefreshBalancesHandler } from '../handlers/refresh-balances';
import { SocketMessageType } from '../types/base';

export function createBusinessRegistry(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): Pick<
  MessageHandlerRegistry,
  | typeof SocketMessageType.ACCOUNTING_RULE_CONFLICT
  | typeof SocketMessageType.CALENDAR_REMINDER
  | typeof SocketMessageType.DATABASE_UPLOAD_PROGRESS
  | typeof SocketMessageType.DB_UPLOAD_RESULT
  | typeof SocketMessageType.EXCHANGE_UNKNOWN_ASSET
  | typeof SocketMessageType.NEW_TOKEN_DETECTED
  | typeof SocketMessageType.HISTORICAL_BALANCE_PROCESSING_COMPLETED
  | typeof SocketMessageType.REFRESH_BALANCES
> {
  const newTokenDetectedHandler = createNewTokenDetectedHandler(t, router);
  const accountingRuleConflictHandler = createAccountingRuleConflictHandler(t, router);
  const calendarReminderHandler = createCalendarReminderHandler(t, router);
  const exchangeUnknownAssetHandler = createExchangeUnknownAssetHandler(t, router);

  return {
    [SocketMessageType.ACCOUNTING_RULE_CONFLICT]: accountingRuleConflictHandler,
    [SocketMessageType.CALENDAR_REMINDER]: calendarReminderHandler,
    [SocketMessageType.DATABASE_UPLOAD_PROGRESS]: createDbUploadProgressHandler(),
    [SocketMessageType.DB_UPLOAD_RESULT]: createDbUploadResultHandler(),
    [SocketMessageType.EXCHANGE_UNKNOWN_ASSET]: exchangeUnknownAssetHandler,
    [SocketMessageType.NEW_TOKEN_DETECTED]: newTokenDetectedHandler,
    [SocketMessageType.HISTORICAL_BALANCE_PROCESSING_COMPLETED]: createHistoricalBalanceProcessingCompletedHandler(),
    [SocketMessageType.REFRESH_BALANCES]: createRefreshBalancesHandler(),
  };
}
