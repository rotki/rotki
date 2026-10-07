import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { HistoricalBalanceDivergencePayload, HistoricalBalanceDivergenceResponse } from '@/modules/history/balances/types';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useArchiveNodes } from '@/modules/history/balances/use-archive-nodes';
import { type DivergenceBoundaryEvent, useBalanceDivergence } from '@/modules/history/balances/use-balance-divergence';
import { IssueKind } from '@/modules/history/data-issues/constants';
import { PinnedNames } from '@/modules/session/types';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

interface UseDataIssueDivergenceReturn {
  available: ComputedRef<boolean>;
  boundaries: ComputedRef<DivergenceBoundaryEvent[]>;
  canSearch: ComputedRef<boolean>;
  chain: ComputedRef<string | undefined>;
  error: Readonly<Ref<string | undefined>>;
  loading: Readonly<Ref<boolean>>;
  missingArchive: ComputedRef<boolean>;
  search: () => Promise<void>;
  summary: ComputedRef<string | undefined>;
  view: (boundary: DivergenceBoundaryEvent) => void;
}

/** Searches the affected EVM wallet through the issue's timestamp, excluding later corrections. */
export function useDataIssueDivergence(
  issue: MaybeRefOrGetter<DataIssue>,
  initialResult?: MaybeRefOrGetter<HistoricalBalanceDivergenceResponse | undefined>,
): UseDataIssueDivergenceReturn {
  const { getEvmChainName, matchChain } = useSupportedChains();
  const divergence = useBalanceDivergence(initialResult);
  const { pin } = usePinnedPanel(PinnedNames.BALANCE_DIVERGENCE);

  const chain = computed<string | undefined>(() => matchChain(toValue(issue).location));
  const payload = computed<HistoricalBalanceDivergencePayload | undefined>(() => {
    const current = toValue(issue);
    const selectedChain = get(chain);
    const evmChain = selectedChain ? getEvmChainName(selectedChain) : undefined;
    const balanceIssue = current.kind === IssueKind.NEGATIVE_BALANCE
      || current.kind === IssueKind.CURRENT_BALANCE_MISMATCH;
    if (!isAccountingUpdateEnabled() || !balanceIssue || current.protocol
      || !evmChain || !current.asset || !current.locationLabel) {
      return undefined;
    }

    return {
      address: current.locationLabel,
      asset: current.asset,
      evmChain,
      toTimestamp: current.tsEnd,
    };
  });

  const available = computed<boolean>(() => !!get(payload));
  const { hasArchiveNode, loading: archiveLoading } = useArchiveNodes(() => {
    const selectedChain = get(chain);
    return get(available) && selectedChain ? [selectedChain] : [];
  });
  const hasArchive = hasArchiveNode(chain);
  const missingArchive = computed<boolean>(() => get(available) && !get(archiveLoading) && !get(hasArchive));
  const canSearch = computed<boolean>(() => get(available) && !get(archiveLoading)
    && get(hasArchive) && !get(divergence.loading));

  async function search(): Promise<void> {
    const scope = get(payload);
    if (scope && get(canSearch))
      await divergence.find(scope);
  }

  function view(boundary: DivergenceBoundaryEvent): void {
    const scope = get(payload);
    if (scope) {
      pin({ issue: toValue(issue), result: get(divergence.result) });
      divergence.navigate(boundary.event, scope.asset);
    }
  }

  return {
    available,
    boundaries: divergence.boundaries,
    canSearch,
    chain,
    error: divergence.error,
    loading: divergence.loading,
    missingArchive,
    search,
    summary: divergence.summary,
    view,
  };
}
