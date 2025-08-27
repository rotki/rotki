import type { ExchangeUnknownAssetData } from '../types/business-types';
import type { MessageHandler } from '@/modules/messaging/interfaces';
import { NotificationCategory, NotificationGroup, Severity } from '@rotki/common';
import { pick } from 'es-toolkit';
import { useMissingMappingsDB } from '@/modules/asset-manager/missing-mappings/use-missing-mappings-db';
import { createStateWithNotificationHandler } from '@/modules/messaging/utils';
import { Routes } from '@/router/routes';

export function createExchangeUnknownAssetHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): MessageHandler<ExchangeUnknownAssetData> {
  return createStateWithNotificationHandler<ExchangeUnknownAssetData, number>(
    // State update function - stores the mapping and returns count
    async (data) => {
      const { count, put } = useMissingMappingsDB();
      const mapping = pick(data, ['identifier', 'location', 'name', 'details']);

      await put(mapping); // This will be caught by the factory's error handling
      return count();
    },
    // Notification function - creates notification based on the count
    async (data, groupCount) => ({
      action: {
        action: async () => router.push({
          path: Routes.ASSET_MANAGER_MISSING_MAPPINGS.toString(),
        }),
        icon: 'lu-cable',
        label: t('asset_management.cex_mapping.add_mapping'),
      },
      category: NotificationCategory.DEFAULT,
      display: true,
      group: NotificationGroup.MISSING_EXCHANGE_MAPPING,
      groupCount,
      message: t('notification_messages.unknown_asset_mapping.message', { groupCount }),
      severity: Severity.WARNING,
      title: t('notification_messages.unknown_asset_mapping.title'),
    }),
  );
}
