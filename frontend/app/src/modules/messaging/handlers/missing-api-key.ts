import type { NotificationHandler } from '../interfaces';
import type { MissingApiKey } from '@/modules/messaging/types';
import { type NotificationAction, NotificationCategory, Priority, Severity, toHumanReadable } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { useInterop } from '@/composables/electron-interop';
import { createNotificationHandler } from '@/modules/messaging/utils';
import { Routes } from '@/router/routes';
import { useConfirmStore } from '@/store/confirm';
import { useSettingsStore } from '@/store/settings';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { SUPPRESSIBLE_SERVICES, SuppressibleMissingKeyService } from '@/types/user';
import { getServiceRegisterUrl } from '@/utils/url';

function isSuppressibleService(service: string): service is SuppressibleMissingKeyService {
  return Array.prototype.includes.call(SUPPRESSIBLE_SERVICES, service);
}

export function createMissingApiKeyHandler(t: ReturnType<typeof useI18n>['t'], router: ReturnType<typeof useRouter>): NotificationHandler<MissingApiKey> {
  // Capture interop functions at handler creation time (in setup context)
  const { openUrl } = useInterop();
  const { update } = useSettingsStore();
  const { suppressMissingKeyMsgServices } = storeToRefs(useGeneralSettingsStore());
  const { show } = useConfirmStore();

  return createNotificationHandler<MissingApiKey>((data) => {
    const { service } = data;
    const { external, route } = getServiceRegisterUrl(service) ?? { external: undefined, route: undefined };

    const actions: NotificationAction[] = [];

    const isEtherscan = service === SuppressibleMissingKeyService.ETHERSCAN;

    if (route) {
      actions.push({
        action: async () => router.push(route),
        label: t('notification_messages.missing_api_key.action'),
        persist: true,
      });
    }

    if (isEtherscan) {
      actions.push({
        action: async () => router.push({ path: Routes.SETTINGS_EVM.toString(), hash: '#indexer' }),
        icon: 'lu-settings',
        label: t('notification_messages.missing_api_key.change_indexer_order'),
        persist: true,
      });
    }
    else if (external) {
      actions.push({
        action: async () => openUrl(external),
        icon: 'lu-external-link',
        label: t('notification_messages.missing_api_key.get_key'),
        persist: true,
      });
    }

    // "Do not show again" action - adds service to suppress list with confirmation
    if (isSuppressibleService(service)) {
      const serviceName = toHumanReadable(service, 'capitalize');
      actions.push({
        action: async () => {
          show(
            {
              message: t('notification_messages.missing_api_key.suppress_confirm.message', { service: serviceName }),
              title: t('notification_messages.missing_api_key.suppress_confirm.title'),
            },
            async () => {
              const currentList = get(suppressMissingKeyMsgServices);
              if (!currentList.includes(service)) {
                await update({ suppressMissingKeyMsgServices: [...currentList, service] });
              }
            },
          );
        },
        icon: 'lu-bell-off',
        danger: true,
        label: t('notification_messages.missing_api_key.do_not_show_again'),
      });
    }

    const metadata = {
      ...data,
      service: toHumanReadable(service, 'capitalize'),
    };

    const serviceConfig: Record<string, {
      category: NotificationCategory;
      messageKey: string;
      titleKey: string;
    }> = {
      [SuppressibleMissingKeyService.BEACONCHAIN]: {
        category: NotificationCategory.BEACONCHAIN,
        messageKey: 'notification_messages.missing_api_key.beaconchain.message',
        titleKey: 'notification_messages.missing_api_key.beaconchain.title',
      },
      [SuppressibleMissingKeyService.ETHERSCAN]: {
        category: NotificationCategory.ETHERSCAN,
        messageKey: 'notification_messages.missing_api_key.etherscan.message',
        titleKey: 'notification_messages.missing_api_key.etherscan.title',
      },
      [SuppressibleMissingKeyService.HELIUS]: {
        category: NotificationCategory.HELIUS,
        messageKey: 'notification_messages.missing_api_key.helius.message',
        titleKey: 'notification_messages.missing_api_key.helius.title',
      },
      [SuppressibleMissingKeyService.THEGRAPH]: {
        category: NotificationCategory.THEGRAPH,
        messageKey: 'notification_messages.missing_api_key.thegraph.message',
        titleKey: 'notification_messages.missing_api_key.thegraph.title',
      },
    };

    const config = serviceConfig[service] || serviceConfig[SuppressibleMissingKeyService.ETHERSCAN];
    const { category, messageKey, titleKey } = config;
    const theGraphWarning = service === SuppressibleMissingKeyService.THEGRAPH;

    return {
      action: actions,
      category,
      display: true,
      i18nParam: {
        choice: 0,
        message: messageKey,
        props: {
          ...metadata,
          url: external ?? '',
          ...(theGraphWarning && { docsUrl: externalLinks.usageGuideSection.theGraphApiKey }),
        },
      },
      message: '',
      priority: Priority.ACTION,
      severity: Severity.WARNING,
      title: t(titleKey, metadata),
    };
  });
}
