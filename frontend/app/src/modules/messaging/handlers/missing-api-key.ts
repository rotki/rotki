import type { NotificationHandler } from '../interfaces';
import type { MissingApiKey } from '../types/notification-types';
import { type NotificationAction, NotificationCategory, Priority, Severity, toHumanReadable } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { useInterop } from '@/composables/electron-interop';
import { getServiceRegisterUrl } from '@/utils/url';
import { createNotificationHandler } from '../utils/handler-factories';

export function createMissingApiKeyHandler(t: ReturnType<typeof useI18n>['t'], router: ReturnType<typeof useRouter>): NotificationHandler<MissingApiKey> {
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
      const { openUrl } = useInterop();

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

    const theGraphWarning = service === 'thegraph';

    return {
      action: actions,
      category: NotificationCategory.ETHERSCAN,
      i18nParam: {
        choice: 0,
        message: theGraphWarning
          ? 'notification_messages.missing_api_key.thegraph.message'
          : 'notification_messages.missing_api_key.etherscan.message',
        props: {
          ...metadata,
          url: external ?? '',
          ...(theGraphWarning && { docsUrl: externalLinks.usageGuideSection.theGraphApiKey }),
        },
      },
      message: '',
      priority: Priority.ACTION,
      severity: Severity.WARNING,
      title: theGraphWarning
        ? t('notification_messages.missing_api_key.thegraph.title', metadata)
        : t('notification_messages.missing_api_key.etherscan.title', metadata),
    };
  });
}
