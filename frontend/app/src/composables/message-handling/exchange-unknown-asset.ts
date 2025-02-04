import { type Notification, Severity } from '@rotki/common';
import { Routes } from '@/router/routes';
import type { CommonMessageHandler, ExchangeUnknownAssetData } from '@/types/websocket-messages';

export function useExchangeUnknownAssetHandler(t: ReturnType<typeof useI18n>['t']): CommonMessageHandler<ExchangeUnknownAssetData> {
  const router = useRouter();

  const handle = (data: ExchangeUnknownAssetData): Notification => {
    const {
      details,
      identifier,
      location,
      name,
    } = data;

    return {
      action: {
        action: async () => router.push({
          path: Routes.ASSET_MANAGER_CEX_MAPPING.toString(),
          query: {
            add: 'true',
            location,
            locationSymbol: identifier,
          },
        }),
        icon: 'lu-cable',
        label: t('asset_management.cex_mapping.add_mapping'),
      },
      display: true,
      message: t('notification_messages.unknown_asset_mapping.message', { details, identifier, location, name }),
      severity: Severity.WARNING,
      title: t('notification_messages.unknown_asset_mapping.title', { location }),
    };
  };

  return { handle };
};
