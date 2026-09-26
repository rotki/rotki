import type { Router } from 'vue-router';
import type { MessageHandler } from '../interfaces';
import type { NoAvailableIndexersData } from '@/modules/core/messaging/types';
import { type NotificationAction, NotificationCategory, NotificationGroup, Priority, Severity } from '@rotki/common';
import { getServiceRegisterUrl } from '@/modules/core/common/helpers/url';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

/**
 * Sent by the backend when etherscan refused the chain for the configured key, which happens on
 * the chains its free tier does not cover, and no other indexer could serve it either. The
 * blockscout variant is sent when blockscout is in the chain's order but has no key yet, so a
 * free blockscout key would also restore the queries.
 */
const BLOCKSCOUT_OR_PAID_ETHERSCAN_KEY_REQUIRED = 'blockscout_or_paid_etherscan_key_required';
const ETHERSCAN_PAID_KEY_REQUIRED = 'etherscan_paid_key_required';

function getKeyAction(
  t: ReturnType<typeof useI18n>['t'],
  router: Pick<Router, 'push'>,
  reason?: string,
): NotificationAction | undefined {
  let service: 'blockscout' | 'etherscan' | undefined;
  if (reason === BLOCKSCOUT_OR_PAID_ETHERSCAN_KEY_REQUIRED)
    service = 'blockscout';
  else if (reason === ETHERSCAN_PAID_KEY_REQUIRED)
    service = 'etherscan';

  if (!service)
    return undefined;
  const route = getServiceRegisterUrl(service)?.route;
  if (!route)
    return undefined;

  return {
    action: async () => router.push(route),
    label: service === 'blockscout'
      ? t('notification_messages.no_available_indexers.enter_blockscout_key')
      : t('notification_messages.no_available_indexers.enter_etherscan_key'),
    persist: true,
  };
}

function getNotificationContent(
  t: ReturnType<typeof useI18n>['t'],
  chainName: string,
  reason?: string,
): { message: string; title: string } {
  if (reason === BLOCKSCOUT_OR_PAID_ETHERSCAN_KEY_REQUIRED) {
    return {
      message: t('notification_messages.no_available_indexers.blockscout_or_paid_etherscan_key_required.message', { chain: chainName }),
      title: t('notification_messages.no_available_indexers.blockscout_or_paid_etherscan_key_required.title', { chain: chainName }),
    };
  }

  if (reason === ETHERSCAN_PAID_KEY_REQUIRED) {
    return {
      message: t('notification_messages.no_available_indexers.paid_key_required.message', { chain: chainName }),
      title: t('notification_messages.no_available_indexers.paid_key_required.title', { chain: chainName }),
    };
  }

  return {
    message: t('notification_messages.no_available_indexers.message', { chain: chainName }),
    title: t('notification_messages.no_available_indexers.title'),
  };
}

export function createNoAvailableIndexersHandler(t: ReturnType<typeof useI18n>['t'], router: Pick<Router, 'push'>): MessageHandler<NoAvailableIndexersData> {
  const { updateFrontendSetting } = useSettingsOperations();
  const suppressNoIndexerChains = useSetting('suppressNoIndexerChains');
  const { getChainName } = useSupportedChains();
  const { show } = useConfirmStore();

  return createConditionalHandler<NoAvailableIndexersData>(({ chain, reason }) => {
    if (get(suppressNoIndexerChains).includes(chain))
      return null;

    const chainName = getChainName(chain);
    const { message, title } = getNotificationContent(t, chainName, reason);

    const actions: NotificationAction[] = [];
    const keyAction = getKeyAction(t, router, reason);
    if (keyAction)
      actions.push(keyAction);
    actions.push(
      {
        action: async () => router.push({ name: '/settings/chains/', hash: '#indexer' }),
        label: t('notification_messages.no_available_indexers.action'),
        persist: true,
      },
      {
        action: async (): Promise<void> => {
          show(
            {
              message: t('notification_messages.no_available_indexers.suppress_confirm.message', { chain: chainName }),
              title: t('notification_messages.no_available_indexers.suppress_confirm.title'),
            },
            async () => {
              const currentList = get(suppressNoIndexerChains);
              if (!currentList.includes(chain))
                await updateFrontendSetting({ suppressNoIndexerChains: [...currentList, chain] });
            },
          );
        },
        danger: true,
        icon: 'lu-bell-off',
        label: t('notification_messages.no_available_indexers.do_not_show_again'),
      },
    );

    return {
      action: actions,
      category: NotificationCategory.DEFAULT,
      display: true,
      // Per chain: each chain has its own missing indexers and its own suppression entry, so they
      // must not collapse into one notification that only ever shows the chain that arrived last.
      group: `${NotificationGroup.NO_AVAILABLE_INDEXERS}:${chain}`,
      message,
      priority: Priority.ACTION,
      severity: Severity.WARNING,
      title,
    };
  });
}
