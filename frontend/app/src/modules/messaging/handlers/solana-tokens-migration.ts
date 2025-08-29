import type { MessageHandler } from '../interfaces';
import type { SolanaTokensMigrationData } from '@/modules/messaging/types';
import { NotificationCategory, Severity } from '@rotki/common';
import { useSolanaTokenMigrationStore } from '@/modules/asset-manager/solana-token-migration/solana-token-migration-store';
import { createStateWithNotificationHandler } from '@/modules/messaging/utils';
import { Routes } from '@/router/routes';

export function createSolanaTokensHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): MessageHandler<SolanaTokensMigrationData> {
  // Capture store at handler creation time (in setup context)
  const store = useSolanaTokenMigrationStore();

  return createStateWithNotificationHandler<SolanaTokensMigrationData>(
    (data) => {
      store.setIdentifiers(data.identifiers);
    },
    data => ({
      action: {
        action: async () => router.push(Routes.ASSET_MANAGER_SOLANA_TOKEN_MIGRATION.toString()),
        icon: 'lu-arrow-right',
        label: t('notification_messages.solana_tokens_migration.action'),
        persist: true,
      },
      category: NotificationCategory.DEFAULT,
      display: true,
      message: t('notification_messages.solana_tokens_migration.message', {
        tokens: data.identifiers.map(item => `- ${item}`).join('\n'),
      }),
      severity: Severity.WARNING,
      title: t('notification_messages.solana_tokens_migration.title'),
    }),
  );
}
