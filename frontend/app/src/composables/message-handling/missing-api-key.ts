import { type Blockchain, type Notification, type NotificationAction, Priority, Severity } from '@rotki/common';
import type { CommonMessageHandler, MissingApiKey } from '@/types/websocket-messages';

export function useMissingApiKeyHandler(t: ReturnType<typeof useI18n>['t']): CommonMessageHandler<MissingApiKey> {
  const { getChainName } = useSupportedChains();
  const router = useRouter();

  const handle = (data: MissingApiKey): Notification => {
    const { service, location } = data;
    const { route, external } = getServiceRegisterUrl(service, location) ?? { route: undefined, external: undefined };
    const locationName = get(getChainName(location as Blockchain));

    const actions: NotificationAction[] = [];

    if (route) {
      actions.push({
        label: t('notification_messages.missing_api_key.action'),
        action: async () => await router.push(route),
        persist: true,
      });
    }

    if (external) {
      const { openUrl } = useInterop();

      actions.push({
        label: t('notification_messages.missing_api_key.get_key'),
        icon: 'external-link-line',
        action: () => openUrl(external),
        persist: true,
      });
    }

    const metadata = {
      service: toHumanReadable(service, 'capitalize'),
      location: toHumanReadable(locationName, 'capitalize'),
    };

    const theGraphWarning = service === 'thegraph';

    return {
      title: theGraphWarning
        ? t('notification_messages.missing_api_key.thegraph.title', metadata)
        : t('notification_messages.missing_api_key.etherscan.title', metadata),
      message: '',
      i18nParam: {
        message: theGraphWarning
          ? 'notification_messages.missing_api_key.thegraph.message'
          : 'notification_messages.missing_api_key.etherscan.message',
        choice: 0,
        props: {
          ...metadata,
          key: location,
          url: external ?? '',
          ...(theGraphWarning && { docsUrl: externalLinks.usageGuideSection.theGraphApiKey }),
        },
      },
      severity: Severity.WARNING,
      priority: Priority.ACTION,
      action: actions,
    };
  };

  return { handle };
}
