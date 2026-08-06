import type { Router } from 'vue-router';
import type { MessageHandler } from '../interfaces';
import type { NoAvailableIndexersData } from '@/modules/core/messaging/types';
import { type NotificationAction, NotificationCategory, NotificationGroup, Priority, Severity } from '@rotki/common';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

export function createNoAvailableIndexersHandler(t: ReturnType<typeof useI18n>['t'], router: Pick<Router, 'push'>): MessageHandler<NoAvailableIndexersData> {
  const { updateFrontendSetting } = useSettingsOperations();
  const suppressNoIndexerChains = useSetting('suppressNoIndexerChains');
  const { getChainName } = useSupportedChains();
  const { show } = useConfirmStore();

  return createConditionalHandler<NoAvailableIndexersData>(({ chain }) => {
    if (get(suppressNoIndexerChains).includes(chain))
      return null;

    const chainName = getChainName(chain);

    const actions: NotificationAction[] = [
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
    ];

    return {
      action: actions,
      category: NotificationCategory.DEFAULT,
      display: true,
      // Per chain: each chain has its own missing indexers and its own suppression entry, so they
      // must not collapse into one notification that only ever shows the chain that arrived last.
      group: `${NotificationGroup.NO_AVAILABLE_INDEXERS}:${chain}`,
      message: t('notification_messages.no_available_indexers.message', { chain: chainName }),
      priority: Priority.ACTION,
      severity: Severity.WARNING,
      title: t('notification_messages.no_available_indexers.title'),
    };
  });
}
