import type { MessageHandlerRegistry } from '../interfaces';
import { createExchangeUnknownAssetHandler } from '@/modules/assets/admin/missing-mappings/exchange-unknown-asset-handler';
import { createNewTokenDetectedHandler } from '@/modules/assets/detection/new-token-detected-handler';
import { createAccountingRuleConflictHandler } from '../handlers/accounting-rule-conflict';
import { createCalendarReminderHandler } from '../handlers/calendar-reminder';
import { createDbUploadProgressHandler, createDbUploadResultHandler } from '../handlers/database-upload';
import { createRefreshBalancesHandler } from '../handlers/refresh-balances';
import { SocketMessageType } from '../types/base';

export function createBusinessRegistry(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): Partial<MessageHandlerRegistry> {
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
    [SocketMessageType.REFRESH_BALANCES]: createRefreshBalancesHandler(),
  };
}
