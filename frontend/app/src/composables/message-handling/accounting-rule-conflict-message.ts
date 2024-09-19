import { type Notification, Priority, Severity } from '@rotki/common';
import type { AccountingRuleConflictData, CommonMessageHandler } from '@/types/websocket-messages';

export function useAccountingRuleConflictMessageHandler(t: ReturnType<typeof useI18n>['t']): CommonMessageHandler<AccountingRuleConflictData> {
  const router = useRouter();

  const handle = (data: AccountingRuleConflictData): Notification => {
    const { numOfConflicts } = data;

    return {
      title: t('notification_messages.accounting_rule_conflict.title'),
      message: t('notification_messages.accounting_rule_conflict.message', { conflicts: numOfConflicts }),
      display: true,
      severity: Severity.WARNING,
      priority: Priority.ACTION,
      action: {
        label: t('notification_messages.accounting_rule_conflict.action'),
        action: async (): Promise<void> => {
          await router.push({
            path: '/settings/accounting',
            query: { resolveConflicts: 'true' },
          });
        },
      },
    };
  };

  return { handle };
};
