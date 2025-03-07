import type { AccountingRuleConflictData, CommonMessageHandler } from '@/types/websocket-messages';
import { type Notification, Priority, Severity } from '@rotki/common';

export function useAccountingRuleConflictMessageHandler(t: ReturnType<typeof useI18n>['t']): CommonMessageHandler<AccountingRuleConflictData> {
  const router = useRouter();

  const handle = (data: AccountingRuleConflictData): Notification => {
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
      display: true,
      message: t('notification_messages.accounting_rule_conflict.message', { conflicts: numOfConflicts }),
      priority: Priority.ACTION,
      severity: Severity.WARNING,
      title: t('notification_messages.accounting_rule_conflict.title'),
    };
  };

  return { handle };
};
