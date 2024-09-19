import { type Notification, Severity } from '@rotki/common';
import { Routes } from '@/router/routes';
import type { CommonMessageHandler, ExchangeUnknownAssetData } from '@/types/websocket-messages';

export function useExchangeUnknownAssetHandler(t: ReturnType<typeof useI18n>['t']): CommonMessageHandler<ExchangeUnknownAssetData> {
  const router = useRouter();

  const handle = (data: ExchangeUnknownAssetData): Notification => {
    const {
      location,
      name,
      details,
      identifier,
    } = data;

    return {
      title: t('notification_messages.unknown_asset_mapping.title', { location }),
      message: t('notification_messages.unknown_asset_mapping.message', { location, identifier, name, details }),
      display: true,
      severity: Severity.WARNING,
      action: {
        label: t('notification_messages.unknown_asset_mapping.actions.add_mapping'),
        icon: 'guide-line',
        action: async () => await router.push({
          path: Routes.ASSET_MANAGER_CEX_MAPPING.toString(),
          query: {
            add: 'true',
            locationSymbol: identifier,
            location,
          },
        }),
      },
    };
  };

  return { handle };
};
