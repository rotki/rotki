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
 * the chains its free tier does not cover, and no other indexer could serve it either.
 */
const ETHERSCAN_PAID_KEY_REQUIRED = 'etherscan_paid_key_required';

export function createNoAvailableIndexersHandler(t: ReturnType<typeof useI18n>['t'], router: Pick<Router, 'push'>): MessageHandler<NoAvailableIndexersData> {
  const { updateFrontendSetting } = useSettingsOperations();
  const suppressNoIndexerChains = useSetting('suppressNoIndexerChains');
  const { getChainName } = useSupportedChains();
  const { show } = useConfirmStore();

  return createConditionalHandler<NoAvailableIndexersData>(({ chain, reason }) => {
    if (get(suppressNoIndexerChains).includes(chain))
      return null;

    const chainName = getChainName(chain);
    const paidKeyRequired = reason === ETHERSCAN_PAID_KEY_REQUIRED;
    const etherscanRoute = getServiceRegisterUrl('etherscan')?.route;

    const actions: NotificationAction[] = [];
    if (paidKeyRequired && etherscanRoute) {
      actions.push({
        action: async () => router.push(etherscanRoute),
        label: t('notification_messages.no_available_indexers.enter_key'),
        persist: true,
      });
    }
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
      message: paidKeyRequired
        ? t('notification_messages.no_available_indexers.paid_key_required.message', { chain: chainName })
        : t('notification_messages.no_available_indexers.message', { chain: chainName }),
      priority: Priority.ACTION,
      severity: Severity.WARNING,
      title: paidKeyRequired
        ? t('notification_messages.no_available_indexers.paid_key_required.title', { chain: chainName })
        : t('notification_messages.no_available_indexers.title'),
    };
  });
}
