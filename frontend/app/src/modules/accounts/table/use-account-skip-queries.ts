import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';
import { useSkipAddressQueries } from '@/modules/settings/general/disabled-chain-queries/use-skip-address-queries';

/** `PARTIAL` is the state a per-chain choice creates, and the reason the row cannot be a checkbox. */
export const SkipState = {
  ALL: 'all',
  NONE: 'none',
  PARTIAL: 'partial',
} as const;

export type SkipState = (typeof SkipState)[keyof typeof SkipState];

export interface SkipChainItem {
  readonly chain: string;
  readonly name: string;
  readonly skipped: boolean;
  /** The chain is switched off whole, so nothing this row does can change it. */
  readonly wholeChain: boolean;
}

export interface UseAccountSkipQueriesReturn {
  /** One entry per chain of the row, in the row's own order, whole-chain ones included. */
  items: ComputedRef<SkipChainItem[]>;
  state: ComputedRef<SkipState>;
  /** No chain in scope can carry a per-address rule, so the row has nothing to offer. */
  locked: ComputedRef<boolean>;
  pending: Readonly<Ref<boolean>>;
  /** Skip every chain the row can act on, or resume them all when they are already skipped. */
  toggleAll: () => Promise<void>;
  toggleChain: (chain: string) => Promise<void>;
}

/**
 * One account row's view of the `disabledChainQueries` setting: the per-chain state behind the
 * row's control, and the two writes it offers.
 *
 * @remarks
 * Chains switched off whole are listed but never written to, in either direction: that is a
 * decision about the chain, and a row lifting it would silently re-enable every other address on
 * it. They are excluded from {@link SkipState} for the same reason - a row whose only chain is off
 * whole reads as `none`, with `locked` explaining why nothing can be done about it.
 *
 * A failed write reports itself here rather than in the component, because the component would
 * otherwise have to repeat it for each of the two actions.
 */
export function useAccountSkipQueries(
  address: MaybeRefOrGetter<string>,
  chains: MaybeRefOrGetter<string[]>,
): UseAccountSkipQueriesReturn {
  const { t } = useI18n({ useScope: 'global' });

  const pending = shallowRef<boolean>(false);

  const { setMessage } = useMessageStore();
  const { getChainName } = useSupportedChains();
  const { isChainExcluded } = useDisabledChains();
  const { isSkipped, toggle } = useSkipAddressQueries();

  const items = computed<SkipChainItem[]>(() => toValue(chains).map(chain => ({
    chain,
    name: getChainName(chain),
    skipped: isSkipped(toValue(address), [chain]),
    wholeChain: isChainExcluded(chain),
  })));

  const skippable = computed<SkipChainItem[]>(() => get(items).filter(item => !item.wholeChain));

  const locked = computed<boolean>(() => get(skippable).length === 0);

  const state = computed<SkipState>(() => {
    const actionable = get(skippable);
    const skipped = actionable.filter(item => item.skipped).length;
    if (skipped === 0)
      return SkipState.NONE;
    return skipped === actionable.length ? SkipState.ALL : SkipState.PARTIAL;
  });

  const run = async (write: () => Promise<ActionStatus>): Promise<void> => {
    set(pending, true);
    const result = await write();
    set(pending, false);
    if (!result.success) {
      setMessage({
        description: result.message,
        success: false,
        title: t('account_balances.skip_queries.error'),
      });
    }
  };

  const toggleAll = async (): Promise<void> => run(async () => toggle(toValue(address), toValue(chains)));

  const toggleChain = async (chain: string): Promise<void> => run(async () => toggle(toValue(address), [chain]));

  return {
    items,
    locked,
    pending: readonly(pending),
    state,
    toggleAll,
    toggleChain,
  };
}
