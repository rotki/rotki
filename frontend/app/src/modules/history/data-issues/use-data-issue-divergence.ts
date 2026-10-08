import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { HistoricalBalanceDivergencePayload, HistoricalBalanceDivergenceResponse } from '@/modules/history/balances/types';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useArchiveNodes } from '@/modules/history/balances/use-archive-nodes';
import { type DivergenceBoundaryEvent, useBalanceDivergence } from '@/modules/history/balances/use-balance-divergence';
import { IssueKind } from '@/modules/history/data-issues/constants';
import { dataIssueDivergenceKey, useDataIssueDivergenceStore } from '@/modules/history/data-issues/use-data-issue-divergence-store';
import { PinnedNames } from '@/modules/session/types';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

interface UseDataIssueDivergenceReturn {
  available: ComputedRef<boolean>;
  boundaries: ComputedRef<DivergenceBoundaryEvent[]>;
  canSearch: ComputedRef<boolean>;
  chain: ComputedRef<string | undefined>;
  chainName: ComputedRef<string>;
  checkingArchive: Readonly<Ref<boolean>>;
  error: Readonly<Ref<string | undefined>>;
  loading: ComputedRef<boolean>;
  missingArchive: ComputedRef<boolean>;
  search: () => Promise<void>;
  status: ComputedRef<HistoricalBalanceDivergenceResponse['status'] | undefined>;
  summary: ComputedRef<string | undefined>;
  view: (boundary: DivergenceBoundaryEvent) => void;
}

/**
 * Searches the affected EVM wallet through the issue's timestamp, excluding later corrections.
 *
 * @remarks
 * The result, error and running state are kept in {@link useDataIssueDivergenceStore}, so a search
 * survives the drawer closing and is shared with the pinned rail showing the same issue.
 */
export function useDataIssueDivergence(issue: MaybeRefOrGetter<DataIssue>): UseDataIssueDivergenceReturn {
  const { getChainName, getEvmChainName, matchChain } = useSupportedChains();
  const store = useDataIssueDivergenceStore();
  const { errors, results, running } = storeToRefs(store);
  const key = computed<string>(() => dataIssueDivergenceKey(toValue(issue)));
  const divergence = useBalanceDivergence(() => get(results).get(get(key)));
  const { pin } = usePinnedPanel(PinnedNames.BALANCE_DIVERGENCE);

  const chain = computed<string | undefined>(() => matchChain(toValue(issue).location));
  const chainName = computed<string>(() => {
    const selectedChain = get(chain);
    return selectedChain ? getChainName(selectedChain) : '';
  });
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
      toTimestamp: Math.floor(current.tsEnd / 1000),
    };
  });

  const available = computed<boolean>(() => !!get(payload));
  const { hasArchiveNode, loading: checkingArchive } = useArchiveNodes(() => {
    const selectedChain = get(chain);
    return get(available) && selectedChain ? [selectedChain] : [];
  });
  const hasArchive = hasArchiveNode(chain);
  const loading = computed<boolean>(() => get(divergence.loading) || get(running).has(get(key)));
  const missingArchive = computed<boolean>(() => get(available) && !get(checkingArchive) && !get(hasArchive));
  const canSearch = computed<boolean>(() => get(available) && !get(checkingArchive)
    && get(hasArchive) && !get(loading));
  const status = computed<HistoricalBalanceDivergenceResponse['status'] | undefined>(() => get(divergence.result)?.status);
  const error = computed<string | undefined>(() => get(errors).get(get(key)));

  async function search(): Promise<void> {
    const scope = get(payload);
    if (!scope || !get(canSearch))
      return;

    const searchKey = get(key);
    store.setRunning(searchKey, true);
    try {
      await divergence.find(scope);
      store.setResult(searchKey, get(divergence.result));
      store.setError(searchKey, get(divergence.error));
    }
    finally {
      store.setRunning(searchKey, false);
    }
  }

  function view(boundary: DivergenceBoundaryEvent): void {
    const scope = get(payload);
    if (scope) {
      pin({ issue: toValue(issue) });
      divergence.navigate(boundary.event, scope.asset);
    }
  }

  return {
    available,
    boundaries: divergence.boundaries,
    canSearch,
    chain,
    chainName,
    checkingArchive,
    error,
    loading,
    missingArchive,
    search,
    status,
    summary: divergence.summary,
    view,
  };
}
