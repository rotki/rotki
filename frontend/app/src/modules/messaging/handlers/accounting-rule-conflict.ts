import type { NotificationHandler } from '../interfaces';
import type { AccountingRuleConflictData } from '../types/business-types';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { createNotificationHandler } from '@/modules/messaging/utils';

export function createAccountingRuleConflictHandler(t: ReturnType<typeof useI18n>['t'], router: ReturnType<typeof useRouter>): NotificationHandler<AccountingRuleConflictData> {
  return createNotificationHandler<AccountingRuleConflictData>((data) => {
    const { numOfConflicts } = data;

    return {
      action: {
        action: async (): Promise<void> => {
          await router.push({
            path: '/settings/accounting',
            query: { resolveConflicts: 'true' },
          });
        },
        label: t('notification_messages.accounting_rule_conflict.action'),
      },
      category: NotificationCategory.DEFAULT,
      display: true,
      message: t('notification_messages.accounting_rule_conflict.message', { conflicts: numOfConflicts }),
      priority: Priority.ACTION,
      severity: Severity.WARNING,
      title: t('notification_messages.accounting_rule_conflict.title'),
    };
  });
}
