import type { ComputedRef } from 'vue';
import { none, some } from 'plainfp/option';
import { type ActionItem, type ActionItemOption, type ActionTarget, ActionUrgency, applicable, createActionItem } from '@/modules/core/action-center/types';
import { getServiceRegisterUrl } from '@/modules/core/common/helpers/url';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { INDEXER_SETTINGS, useSuppressOption } from '@/modules/shell/action-center/row-options';
import {
  conditionRowId,
  isConditionOf,
  RaisedConditionKind,
  type RaisedConditionOf,
  useRaisedConditionsStore,
} from '@/modules/shell/action-center/use-raised-conditions-store';

type NoIndexersCondition = RaisedConditionOf<typeof RaisedConditionKind.NO_AVAILABLE_INDEXERS>;

const isNoIndexersCondition = isConditionOf(RaisedConditionKind.NO_AVAILABLE_INDEXERS);

/**
 * The chain rows: chains no indexer could serve.
 *
 * @remarks
 * Nothing can ask whether a chain has an indexer again, and the backend reports each chain only once
 * per session, so a row stays until the user suppresses the chain or does what it asks: saving an
 * Etherscan key clears the rows that asked for a paid one. A key that is already saved is no reason
 * to hide a row, since the key Etherscan refused is usually that one.
 */
export function useChainRows(): ComputedRef<ActionItem[]> {
  const { t } = useI18n({ useScope: 'global' });

  const { conditions } = storeToRefs(useRaisedConditionsStore());
  const suppressedChains = useSetting('suppressNoIndexerChains');
  const { getChainName } = useSupportedChains();
  const { updateFrontendSetting } = useSettingsOperations();
  const { suppressOption } = useSuppressOption();

  function isOpen({ chain }: NoIndexersCondition): boolean {
    return !get(suppressedChains).includes(chain);
  }

  async function suppress(chain: string): Promise<void> {
    const current = get(suppressedChains);
    if (!current.includes(chain))
      await updateFrontendSetting({ suppressNoIndexerChains: [...current, chain] });
  }

  function options({ chain, paidKeyRequired }: NoIndexersCondition, chainName: string): ActionItemOption[] {
    return applicable<ActionItemOption>([
      paidKeyRequired
        ? some({
            icon: 'lu-settings',
            id: 'configure-indexers',
            label: t('action_center.rows.chains.no_indexers.action'),
            target: INDEXER_SETTINGS,
          })
        : none,
      some(suppressOption({
        confirmMessage: t('action_center.rows.chains.suppress_confirm.message', { chain: chainName }),
        confirmTitle: t('action_center.rows.chains.suppress_confirm.title', { chain: chainName }),
        label: t('action_center.rows.chains.do_not_show_again'),
        suppress: async () => suppress(chain),
      })),
    ]);
  }

  function row(condition: NoIndexersCondition): ActionItem {
    const chain = getChainName(condition.chain);
    const shared = {
      count: 1,
      icon: 'lu-server',
      id: conditionRowId(condition),
      options: options(condition, chain),
      urgency: ActionUrgency.DECISION,
    } as const;

    if (condition.paidKeyRequired) {
      const etherscanSettings: ActionTarget = {
        kind: 'route',
        to: getServiceRegisterUrl('etherscan')?.route ?? { name: '/api-keys/external/', query: { service: 'etherscan' } },
      };
      return createActionItem<ActionTarget, string>({
        ...shared,
        actionLabel: t('action_center.rows.chains.paid_key_required.action'),
        description: t('action_center.rows.chains.paid_key_required.description', { chain }),
        target: etherscanSettings,
        title: t('action_center.rows.chains.paid_key_required.title', { chain }),
      });
    }

    return createActionItem<ActionTarget, string>({
      ...shared,
      actionLabel: t('action_center.rows.chains.no_indexers.action'),
      description: t('action_center.rows.chains.no_indexers.description', { chain }),
      target: INDEXER_SETTINGS,
      title: t('action_center.rows.chains.no_indexers.title', { chain }),
    });
  }

  return computed<ActionItem[]>(() => get(conditions).filter(isNoIndexersCondition).filter(isOpen).map(row));
}
