import type { MessageHandler } from '@/modules/core/messaging/interfaces';
import type { SolanaTokensMigrationData } from '@/modules/core/messaging/types';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { useSolanaTokenMigrationStore } from '@/modules/assets/admin/solana-token-migration/use-solana-token-migration-store';
import { createStateWithNotificationHandler } from '@/modules/core/messaging/utils';

export function createSolanaTokensHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): MessageHandler<SolanaTokensMigrationData> {
  const store = useSolanaTokenMigrationStore();

  return createStateWithNotificationHandler<SolanaTokensMigrationData>(
    (data) => {
      store.setIdentifiers(data.identifiers);
    },
    data => ({
      action: {
        action: async () => router.push({ name: '/asset-manager/more/solana-token-migration/' }),
        icon: 'lu-arrow-right',
        label: t('notification_messages.solana_tokens_migration.action'),
        persist: true,
      },
      category: NotificationCategory.DEFAULT,
      message: t('notification_messages.solana_tokens_migration.message', {
        tokens: data.identifiers.map(item => `- ${item}`).join('\n'),
      }),
      priority: Priority.ACTION,
      severity: Severity.WARNING,
      title: t('notification_messages.solana_tokens_migration.title'),
    }),
  );
}
