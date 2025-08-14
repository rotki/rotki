import type { CommonMessageHandler, ExchangeUnknownAssetData } from '@/types/websocket-messages';
import { type Notification, NotificationGroup, Severity } from '@rotki/common';
import { pick } from 'es-toolkit';
import { useMissingMappingsDB } from '@/modules/asset-manager/missing-mappings/use-missing-mappings-db';
import { Routes } from '@/router/routes';
import { logger } from '@/utils/logging';

export function useExchangeUnknownAssetHandler(t: ReturnType<typeof useI18n>['t']): CommonMessageHandler<ExchangeUnknownAssetData> {
  const router = useRouter();
  const { count, put } = useMissingMappingsDB();

  const handle = async (data: ExchangeUnknownAssetData): Promise<Notification> => {
    const mapping = pick(data, ['identifier', 'location', 'name', 'details']);

    try {
      await put(mapping);
    }
    catch (error: any) {
      logger.error(error);
    }

    const groupCount = await count();

    return {
      action: {
        action: async () => router.push({
          path: Routes.ASSET_MANAGER_MISSING_MAPPINGS.toString(),
        }),
        icon: 'lu-cable',
        label: t('asset_management.cex_mapping.add_mapping'),
      },
      display: true,
      group: NotificationGroup.MISSING_EXCHANGE_MAPPING,
      groupCount,
      message: t('notification_messages.unknown_asset_mapping.message', { groupCount }),
      severity: Severity.WARNING,
      title: t('notification_messages.unknown_asset_mapping.title'),
    };
  };

  return { handle };
}
