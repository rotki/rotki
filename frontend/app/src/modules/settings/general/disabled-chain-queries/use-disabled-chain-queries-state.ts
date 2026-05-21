import type { MaybeRefOrGetter, Ref } from 'vue';

export type DisabledChainQueries = Record<string, string[]>;

export type RuleKind = 'chain' | 'address';

export interface ChainRule {
  readonly id: string;
  readonly kind: 'chain';
  readonly chainId: string;
}

export interface AddressRule {
  readonly id: string;
  readonly kind: 'address';
  readonly address: string;
  readonly chainIds: readonly string[];
}

export type Rule = ChainRule | AddressRule;

export type RuleDraft =
  | { kind: 'chain'; chainId: string }
  | { kind: 'address'; address: string; chainIds: readonly string[] };

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
  /** Read-only — mutate via {@link addRule}, {@link updateRule}, {@link removeRule}. */
  rules: Readonly<Ref<readonly Rule[]>>;
  /** Build the backend payload from the current rules. */
  buildPayload: () => DisabledChainQueries;
  /**
   * Insert a new rule. Address rules with the same address as an existing one
   * are auto-merged (chainIds union). Returns the payload to commit, or
   * `undefined` if the resulting payload is identical to the last-synced source.
   */
  addRule: (draft: RuleDraft) => DisabledChainQueries | undefined;
  /**
   * Replace the rule at `id` with `draft`. If the replacement is an address
   * rule whose address matches a different existing address rule, the two are
   * auto-merged (chainIds union). Returns the payload to commit or `undefined`
   * on no-op.
   */
  updateRule: (id: string, draft: RuleDraft) => DisabledChainQueries | undefined;
  /** Remove the rule at `id`. Returns the payload to commit or `undefined` on no-op. */
  removeRule: (id: string) => DisabledChainQueries | undefined;
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
    const sortedA = [...av].sort();
    const sortedB = [...bv].sort();
    for (const [i, value] of sortedA.entries()) {
      if (value !== sortedB[i])
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

let ruleIdCounter = 0;

function nextRuleId(): string {
  ruleIdCounter += 1;
  return `rule-${ruleIdCounter}`;
}

function buildPayloadFromRules(rules: readonly Rule[]): DisabledChainQueries {
  const payload: DisabledChainQueries = {};
  const fullyDisabled = new Set<string>();
  for (const rule of rules) {
    if (rule.kind === 'chain') {
      payload[rule.chainId] = [];
      fullyDisabled.add(rule.chainId);
    }
  }
  for (const rule of rules) {
    if (rule.kind !== 'address')
      continue;
    for (const chainId of rule.chainIds) {
      if (fullyDisabled.has(chainId))
        continue;
      const existing = payload[chainId];
      if (existing === undefined)
        payload[chainId] = [rule.address];
      else if (!existing.includes(rule.address))
        existing.push(rule.address);
    }
  }
  return payload;
}

function parsePayload(
  payload: DisabledChainQueries,
  matchChain: (raw: string) => string | undefined,
): Rule[] {
  const rules: Rule[] = [];
  const addressEntries = new Map<string, string[]>();
  for (const [rawChain, addresses] of Object.entries(payload)) {
    const chainId = matchChain(rawChain);
    if (!chainId)
      continue;
    if (addresses.length === 0) {
      rules.push({ chainId, id: nextRuleId(), kind: 'chain' });
      continue;
    }
    for (const address of addresses) {
      const list = addressEntries.get(address);
      if (list === undefined)
        addressEntries.set(address, [chainId]);
      else if (!list.includes(chainId))
        list.push(chainId);
    }
  }
  for (const [address, chainIds] of addressEntries)
    rules.push({ address, chainIds, id: nextRuleId(), kind: 'address' });
  return rules;
}

function mergeAddressRules(rules: readonly Rule[]): Rule[] {
  const merged: Rule[] = [];
  const indexByAddress = new Map<string, number>();
  for (const rule of rules) {
    if (rule.kind === 'chain') {
      merged.push(rule);
      continue;
    }
    const existingIndex = indexByAddress.get(rule.address);
    if (existingIndex === undefined) {
      indexByAddress.set(rule.address, merged.length);
      merged.push(rule);
      continue;
    }
    const existing = merged[existingIndex];
    if (existing.kind !== 'address')
      continue;
    const chainIds = [...existing.chainIds];
    for (const chainId of rule.chainIds) {
      if (!chainIds.includes(chainId))
        chainIds.push(chainId);
    }
    merged[existingIndex] = { ...existing, chainIds };
  }
  return merged;
}

function normalizeDraft(draft: RuleDraft, id: string): Rule {
  if (draft.kind === 'chain')
    return { chainId: draft.chainId, id, kind: 'chain' };
  return { address: draft.address, chainIds: [...draft.chainIds], id, kind: 'address' };
}

export function useDisabledChainQueriesState(
  options: UseDisabledChainQueriesStateOptions,
): UseDisabledChainQueriesStateReturn {
  const { matchChain, ready, source } = options;

  const rules = shallowRef<readonly Rule[]>([]);
  /**
   * Snapshot of the most recently synced (or just-committed) payload. Used to
   * short-circuit setters that would otherwise emit a payload identical to what
   * the backend already has.
   */
  const lastCommittedPayload = ref<DisabledChainQueries>({});

  function buildPayload(): DisabledChainQueries {
    return buildPayloadFromRules(get(rules));
  }

  function commitIfChanged(payload: DisabledChainQueries): DisabledChainQueries | undefined {
    if (payloadsEqual(payload, get(lastCommittedPayload)))
      return undefined;
    set(lastCommittedPayload, clonePayload(payload));
    return payload;
  }

  function applyRules(next: readonly Rule[]): DisabledChainQueries | undefined {
    const merged = mergeAddressRules(next);
    set(rules, merged);
    return commitIfChanged(buildPayloadFromRules(merged));
  }

  function addRule(draft: RuleDraft): DisabledChainQueries | undefined {
    const next = [...get(rules), normalizeDraft(draft, nextRuleId())];
    return applyRules(next);
  }

  function updateRule(id: string, draft: RuleDraft): DisabledChainQueries | undefined {
    const current = get(rules);
    const index = current.findIndex(rule => rule.id === id);
    if (index === -1)
      return undefined;
    const next = [...current];
    next[index] = normalizeDraft(draft, id);
    return applyRules(next);
  }

  function removeRule(id: string): DisabledChainQueries | undefined {
    const current = get(rules);
    const next = current.filter(rule => rule.id !== id);
    if (next.length === current.length)
      return undefined;
    return applyRules(next);
  }

  watch(
    [source, (): boolean => toValue(ready)],
    ([raw, isReady]) => {
      if (!isReady)
        return;
      const parsed = parsePayload(raw, matchChain);
      const nextPayload = buildPayloadFromRules(parsed);
      set(rules, parsed);
      set(lastCommittedPayload, clonePayload(nextPayload));
    },
    { deep: true, immediate: true },
  );

  return {
    addRule,
    buildPayload,
    removeRule,
    rules: readonly(rules),
    updateRule,
  };
}
