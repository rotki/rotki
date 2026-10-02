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
  NoIndexersCause,
  RaisedConditionKind,
  type RaisedConditionOf,
  useRaisedConditionsStore,
} from '@/modules/shell/action-center/use-raised-conditions-store';

type NoIndexersCondition = RaisedConditionOf<typeof RaisedConditionKind.NO_AVAILABLE_INDEXERS>;

const isNoIndexersCondition = isConditionOf(RaisedConditionKind.NO_AVAILABLE_INDEXERS);

/** The causes a key restores, whose row's own action is entering that key. */
const KEY_CAUSES: ReadonlySet<NoIndexersCause> = new Set([
  NoIndexersCause.BLOCKSCOUT_OR_PAID_ETHERSCAN_KEY,
  NoIndexersCause.PAID_ETHERSCAN_KEY,
]);

/** The external services page, opened on the key a row asks for. */
function keySettings(service: 'blockscout' | 'etherscan'): ActionTarget {
  return {
    kind: 'route',
    to: getServiceRegisterUrl(service)?.route ?? { name: '/api-keys/external/', query: { service } },
  };
}

/**
 * The chain rows: chains no indexer could serve.
 *
 * @remarks
 * Nothing can ask whether a chain has an indexer again, and the backend reports each chain only once
 * per reason per session, so a row stays until the user suppresses the chain or does what it asks:
 * saving the key a row asks for clears it. A key that is already saved is no reason to hide a row,
 * since the key Etherscan refused is usually that one.
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

  /**
   * Configuring the indexers, as an option where the row's own action asks for a key, and silencing
   * the chain.
   */
  function options({ cause, chain }: NoIndexersCondition, chainName: string): ActionItemOption[] {
    return applicable<ActionItemOption>([
      KEY_CAUSES.has(cause)
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

    switch (condition.cause) {
      case NoIndexersCause.PAID_ETHERSCAN_KEY:
        return createActionItem<ActionTarget, string>({
          ...shared,
          actionLabel: t('action_center.rows.chains.paid_key_required.action'),
          description: t('action_center.rows.chains.paid_key_required.description', { chain }),
          target: keySettings('etherscan'),
          title: t('action_center.rows.chains.paid_key_required.title', { chain }),
        });
      case NoIndexersCause.BLOCKSCOUT_OR_PAID_ETHERSCAN_KEY:
        return createActionItem<ActionTarget, string>({
          ...shared,
          actionLabel: t('action_center.rows.chains.blockscout_key_required.action'),
          description: t('action_center.rows.chains.blockscout_key_required.description', { chain }),
          target: keySettings('blockscout'),
          title: t('action_center.rows.chains.blockscout_key_required.title', { chain }),
        });
      case NoIndexersCause.UNAVAILABLE:
        return createActionItem<ActionTarget, string>({
          ...shared,
          actionLabel: t('action_center.rows.chains.no_indexers.action'),
          description: t('action_center.rows.chains.no_indexers.description', { chain }),
          target: INDEXER_SETTINGS,
          title: t('action_center.rows.chains.no_indexers.title', { chain }),
        });
    }
  }

  return computed<ActionItem[]>(() => get(conditions).filter(isNoIndexersCondition).filter(isOpen).map(row));
}
