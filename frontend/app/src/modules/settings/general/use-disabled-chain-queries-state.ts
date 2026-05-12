import type { MaybeRefOrGetter, Ref } from 'vue';

export type DisabledChainQueries = Record<string, string[]>;

export interface UseDisabledChainQueriesStateOptions {
  /** Live source of the saved setting (typically a ref from a Pinia store). */
  source: Ref<DisabledChainQueries>;
  /**
   * Truthy when the surrounding app has loaded the supporting data needed to
   * interpret `source` (e.g. the supported-chains list, since unresolved chain
   * names get skipped). Sync from `source` is suspended until `ready` is true so
   * an early user interaction cannot commit a half-initialized payload.
   */
  ready: MaybeRefOrGetter<boolean>;
  /** Normalize a raw chain key from the payload to a frontend chain id, or undefined if unsupported. */
  matchChain: (rawChain: string) => string | undefined;
}

export interface UseDisabledChainQueriesStateReturn {
  /** Read-only — mutate via {@link selectChains}. */
  visibleChainIds: Readonly<Ref<readonly string[]>>;
  /** Read-only — mutate via {@link setExcludedAddresses} or {@link setEntireChainDisabled}. */
  excludedAddresses: Readonly<Ref<Readonly<Record<string, readonly string[]>>>>;
  isEntireChainDisabled: (chainId: string) => boolean;
  isTransientlyDisabled: (chainId: string) => boolean;
  buildPayload: () => DisabledChainQueries;
  /**
   * Replace the visible chain set. Returns the payload to commit, or `undefined`
   * if the resulting payload is identical to the last-synced source (no-op).
   */
  selectChains: (newSelected: string[]) => DisabledChainQueries | undefined;
  /**
   * Flip the "Disable entire chain" toggle. Returns the payload to commit on the ON path
   * (the picker collapses and the address list is cleared) and `undefined` on the OFF path
   * (the picker is revealed but the backend payload is unchanged — the chain stays disabled
   * until at least one address is picked) or when the resulting payload matches the
   * last-synced source.
   */
  setEntireChainDisabled: (chainId: string, disabled: boolean) => DisabledChainQueries | undefined;
  /**
   * Replace the excluded address list for a chain. Returns the payload to commit,
   * or `undefined` if it is identical to the last-synced source (no-op).
   */
  setExcludedAddresses: (chainId: string, addresses: readonly string[]) => DisabledChainQueries | undefined;
}

function payloadsEqual(a: DisabledChainQueries, b: DisabledChainQueries): boolean {
  const aKeys = Object.keys(a);
  const bKeys = Object.keys(b);
  if (aKeys.length !== bKeys.length)
    return false;
  for (const key of aKeys) {
    const av = a[key];
    const bv = b[key];
    if (bv === undefined || av.length !== bv.length)
      return false;
    for (const [i, value] of av.entries()) {
      if (value !== bv[i])
        return false;
    }
  }
  return true;
}

function clonePayload(payload: DisabledChainQueries): DisabledChainQueries {
  const cloned: DisabledChainQueries = {};
  for (const [key, value] of Object.entries(payload))
    cloned[key] = [...value];
  return cloned;
}

export function useDisabledChainQueriesState(
  options: UseDisabledChainQueriesStateOptions,
): UseDisabledChainQueriesStateReturn {
  const { matchChain, ready, source } = options;

  const visibleChainIds = ref<string[]>([]);
  const excludedAddresses = ref<DisabledChainQueries>({});
  // Session-only: chains where the user has explicitly clicked the toggle OFF.
  // The picker is shown even when addresses are empty. On refresh the set is empty,
  // so chains with empty payloads correctly render as "entire chain disabled".
  const pickerRevealedFor = ref<Set<string>>(new Set());
  // Snapshot of the most recently synced (or just-committed) payload. Used to
  // short-circuit setters that would otherwise emit a payload identical to what
  // the backend already has — e.g. an on-mount sync that touches refs without the
  // user changing anything, or a redundant click on an already-active toggle.
  const lastCommittedPayload = ref<DisabledChainQueries>({});

  function hasExcludedAddresses(chainId: string): boolean {
    return (get(excludedAddresses)[chainId] ?? []).length > 0;
  }

  function isEntireChainDisabled(chainId: string): boolean {
    if (get(pickerRevealedFor).has(chainId))
      return false;
    return !hasExcludedAddresses(chainId);
  }

  function isTransientlyDisabled(chainId: string): boolean {
    return get(pickerRevealedFor).has(chainId) && !hasExcludedAddresses(chainId);
  }

  function buildPayload(): DisabledChainQueries {
    const payload: DisabledChainQueries = {};
    for (const chain of get(visibleChainIds))
      payload[chain] = [...(get(excludedAddresses)[chain] ?? [])];

    return payload;
  }

  function commitIfChanged(payload: DisabledChainQueries): DisabledChainQueries | undefined {
    if (payloadsEqual(payload, get(lastCommittedPayload)))
      return undefined;
    set(lastCommittedPayload, clonePayload(payload));
    return payload;
  }

  function selectChains(newSelected: string[]): DisabledChainQueries | undefined {
    const previousValue = get(excludedAddresses);
    const nextValue: DisabledChainQueries = {};
    for (const chain of newSelected)
      nextValue[chain] = previousValue[chain] ?? [];

    const revealed = new Set(get(pickerRevealedFor));
    for (const id of [...revealed]) {
      if (!newSelected.includes(id))
        revealed.delete(id);
    }

    set(excludedAddresses, nextValue);
    set(visibleChainIds, [...newSelected]);
    set(pickerRevealedFor, revealed);
    return commitIfChanged(buildPayload());
  }

  function setEntireChainDisabled(
    chainId: string,
    disabled: boolean,
  ): DisabledChainQueries | undefined {
    const revealed = new Set(get(pickerRevealedFor));
    if (disabled) {
      revealed.delete(chainId);
      set(pickerRevealedFor, revealed);
      set(excludedAddresses, { ...get(excludedAddresses), [chainId]: [] });
      return commitIfChanged(buildPayload());
    }
    revealed.add(chainId);
    set(pickerRevealedFor, revealed);
    return undefined;
  }

  function setExcludedAddresses(
    chainId: string,
    addresses: readonly string[],
  ): DisabledChainQueries | undefined {
    set(excludedAddresses, { ...get(excludedAddresses), [chainId]: [...addresses] });
    return commitIfChanged(buildPayload());
  }

  watch(
    [source, (): boolean => toValue(ready)],
    ([raw, isReady]) => {
      if (!isReady)
        return;

      const nextValue: DisabledChainQueries = {};
      const ordered: string[] = [];
      for (const [rawChain, addrs] of Object.entries(raw)) {
        const chain = matchChain(rawChain);
        if (!chain)
          continue;
        nextValue[chain] = [...addrs];
        ordered.push(chain);
      }

      const previousRevealed = get(pickerRevealedFor);
      const nextRevealed = new Set<string>();
      for (const id of ordered) {
        if (previousRevealed.has(id))
          nextRevealed.add(id);
      }

      set(excludedAddresses, nextValue);
      set(visibleChainIds, ordered);
      set(pickerRevealedFor, nextRevealed);
      set(lastCommittedPayload, clonePayload(nextValue));
    },
    { deep: true, immediate: true },
  );

  return {
    buildPayload,
    excludedAddresses: readonly(excludedAddresses),
    isEntireChainDisabled,
    isTransientlyDisabled,
    selectChains,
    setEntireChainDisabled,
    setExcludedAddresses,
    visibleChainIds: readonly(visibleChainIds),
  };
}
