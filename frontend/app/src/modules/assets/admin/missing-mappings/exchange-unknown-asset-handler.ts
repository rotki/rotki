import type { MessageHandler } from '@/modules/core/messaging/interfaces';
import type { ExchangeUnknownAssetData } from '@/modules/core/messaging/types/business-types';
import { NotificationCategory, NotificationGroup, Severity } from '@rotki/common';
import { pick } from 'es-toolkit';
import { useMissingMappingsDB } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-db';
import { createStateWithNotificationHandler } from '@/modules/core/messaging/utils';

export function createExchangeUnknownAssetHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): MessageHandler<ExchangeUnknownAssetData> {
  const { count, put } = useMissingMappingsDB();

  return createStateWithNotificationHandler<ExchangeUnknownAssetData, number>(
    async (data) => {
      const mapping = pick(data, ['identifier', 'location', 'name', 'details']);

      await put(mapping); // This will be caught by the factory's error handling
      return count();
    },
    async (data, groupCount) => ({
      action: {
        action: async () => router.push({
          name: '/asset-manager/more/missing-mappings/',
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
