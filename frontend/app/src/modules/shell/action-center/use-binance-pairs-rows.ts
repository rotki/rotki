import type { ComputedRef } from 'vue';
import type { BinanceAccount } from '@/modules/balances/exchanges/binance-pairs-condition';
import { toHumanReadable } from '@rotki/common';
import { useBinancePairsConditions } from '@/modules/balances/exchanges/use-binance-pairs-conditions';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { type ActionItem, type ActionTarget, ActionUrgency, createActionItem } from '@/modules/core/action-center/types';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useSuppressOption } from '@/modules/shell/action-center/row-options';
import { conditionRowId, RaisedConditionKind } from '@/modules/shell/action-center/use-raised-conditions-store';

interface UseBinancePairsRowsReturn {
  rows: ComputedRef<ActionItem[]>;
  /** Re-reads the listed accounts' pairs. */
  refresh: () => Promise<void>;
}

/** How a suppressed account is stored in `suppressBinancePairsMissing`. */
function suppressionKey({ location, name }: BinanceAccount): string {
  return `${location}:${name}`;
}

/**
 * The Binance rows: accounts whose trades are skipped because no market pairs are selected.
 *
 * @remarks
 * A row waits for the backend's report, which comes only when a trade history query needs the pairs,
 * so an account used for balances alone is never flagged up front. It leaves once pairs are saved,
 * the account is removed or renamed, or the user asks not to be told again about that account.
 */
export function useBinancePairsRows(): UseBinancePairsRowsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { accounts, recheck, settleDisconnected } = useBinancePairsConditions();
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const suppressed = useSetting('suppressBinancePairsMissing');
  const { updateFrontendSetting } = useSettingsOperations();
  const { suppressOption } = useSuppressOption();

  async function suppress(account: BinanceAccount): Promise<void> {
    const current = get(suppressed);
    const key = suppressionKey(account);
    if (!current.includes(key))
      await updateFrontendSetting({ suppressBinancePairsMissing: [...current, key] });
  }

  function row(account: BinanceAccount): ActionItem {
    const params = { exchange: toHumanReadable(account.location, 'capitalize'), name: account.name };
    return createActionItem<ActionTarget, string>({
      actionLabel: t('action_center.rows.integrations.binance_pairs_missing.action'),
      count: 1,
      description: t('action_center.rows.integrations.binance_pairs_missing.description', params),
      icon: 'lu-list-checks',
      id: conditionRowId({ kind: RaisedConditionKind.BINANCE_PAIRS_MISSING, ...account }),
      options: [suppressOption({
        confirmMessage: t('action_center.rows.integrations.binance_pairs_missing.suppress_confirm.message', params),
        confirmTitle: t('action_center.rows.integrations.binance_pairs_missing.suppress_confirm.title', params),
        label: t('action_center.rows.integrations.binance_pairs_missing.do_not_show_again'),
        suppress: async () => suppress(account),
      })],
      urgency: ActionUrgency.DECISION,
      target: { kind: 'route', to: { name: '/api-keys/exchanges/', query: { location: account.location, name: account.name } } },
      title: t('action_center.rows.integrations.binance_pairs_missing.title', params),
    });
  }

  watch(connectedExchanges, settleDisconnected);

  const rows = computed<ActionItem[]>(() => {
    const hidden = get(suppressed);
    return get(accounts).filter(account => !hidden.includes(suppressionKey(account))).map(row);
  });

  return { refresh: recheck, rows };
}
