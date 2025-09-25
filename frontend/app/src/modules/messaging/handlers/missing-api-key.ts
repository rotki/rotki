import type { NotificationHandler } from '../interfaces';
import type { MissingApiKey } from '@/modules/messaging/types';
import { type NotificationAction, NotificationCategory, Priority, Severity, toHumanReadable } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { useInterop } from '@/composables/electron-interop';
import { createNotificationHandler } from '@/modules/messaging/utils';
import { getServiceRegisterUrl } from '@/utils/url';

export function createMissingApiKeyHandler(t: ReturnType<typeof useI18n>['t'], router: ReturnType<typeof useRouter>): NotificationHandler<MissingApiKey> {
  // Capture interop functions at handler creation time (in setup context)
  const { openUrl } = useInterop();

  return createNotificationHandler<MissingApiKey>((data) => {
    const { service } = data;
    const { external, route } = getServiceRegisterUrl(service) ?? { external: undefined, route: undefined };

    const actions: NotificationAction[] = [];

    if (route) {
      actions.push({
        action: async () => router.push(route),
        label: t('notification_messages.missing_api_key.action'),
        persist: true,
      });
    }

    if (external) {
      actions.push({
        action: async () => openUrl(external),
        icon: 'lu-external-link',
        label: t('notification_messages.missing_api_key.get_key'),
        persist: true,
      });
    }

    const metadata = {
      service: toHumanReadable(service, 'capitalize'),
    };

    const serviceConfig: Record<string, {
      category: NotificationCategory;
      messageKey: string;
      titleKey: string;
    }> = {
      etherscan: {
        category: NotificationCategory.ETHERSCAN,
        messageKey: 'notification_messages.missing_api_key.etherscan.message',
        titleKey: 'notification_messages.missing_api_key.etherscan.title',
      },
      helius: {
        category: NotificationCategory.HELIUS,
        messageKey: 'notification_messages.missing_api_key.helius.message',
        titleKey: 'notification_messages.missing_api_key.helius.title',
      },
      thegraph: {
        category: NotificationCategory.THEGRAPH,
        messageKey: 'notification_messages.missing_api_key.thegraph.message',
        titleKey: 'notification_messages.missing_api_key.thegraph.title',
      },
    };

    const config = serviceConfig[service] || serviceConfig.etherscan;
    const { category, messageKey, titleKey } = config;
    const theGraphWarning = service === 'thegraph';

    return {
      action: actions,
      category,
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
