/** What a condition is about. Kebab-case, since each one prefixes the row ids it lands in. */
export const RaisedConditionKind = {
  GNOSIS_PAY_SESSION: 'gnosis-pay-session',
  MISSING_API_KEY: 'missing-api-key',
  MONERIUM_SESSION: 'monerium-session',
  NO_AVAILABLE_INDEXERS: 'no-available-indexers',
} as const;

export type RaisedConditionKind = (typeof RaisedConditionKind)[keyof typeof RaisedConditionKind];

/**
 * A condition the backend reported over the websocket, which stays raised until an event or a
 * check says it is over.
 *
 * @remarks
 * The report is the evidence that the user needs this: a missing key only matters to someone whose
 * queries asked for it, so a row waits for the message rather than checking every service up front.
 */
export type RaisedCondition =
  | { kind: typeof RaisedConditionKind.MISSING_API_KEY; service: string; location?: string }
  | { kind: typeof RaisedConditionKind.NO_AVAILABLE_INDEXERS; chain: string; paidKeyRequired: boolean }
  | { kind: typeof RaisedConditionKind.GNOSIS_PAY_SESSION }
  | { kind: typeof RaisedConditionKind.MONERIUM_SESSION };

/** The raised condition of one kind, narrowed to that kind's fields. */
export type RaisedConditionOf<K extends RaisedConditionKind> = Extract<RaisedCondition, { kind: K }>;

/** Narrows a condition to one kind, so a module can pick out the conditions its rows are about. */
export function isConditionOf<K extends RaisedConditionKind>(kind: K): (condition: RaisedCondition) => condition is RaisedConditionOf<K> {
  return (condition): condition is RaisedConditionOf<K> => condition.kind === kind;
}

/** One entry per subject, so a repeat of the same report replaces the one before it. */
function conditionKey(condition: RaisedCondition): string {
  switch (condition.kind) {
    case RaisedConditionKind.MISSING_API_KEY:
      return `${condition.kind}:${condition.service}`;
    case RaisedConditionKind.NO_AVAILABLE_INDEXERS:
      return `${condition.kind}:${condition.chain}`;
    case RaisedConditionKind.GNOSIS_PAY_SESSION:
    case RaisedConditionKind.MONERIUM_SESSION:
      return condition.kind;
  }
}

/** The id of a condition's row, one per subject and kebab-case since it lands in a `data-testid`. */
export function conditionRowId(condition: RaisedCondition): string {
  return conditionKey(condition).replaceAll(/[:_]/g, '-');
}

export const useRaisedConditionsStore = defineStore('action-center/raised-conditions', () => {
  const raised = shallowRef<Record<string, RaisedCondition>>({});

  const conditions = computed<RaisedCondition[]>(() => Object.values(get(raised)));

  function raise(condition: RaisedCondition): void {
    set(raised, { ...get(raised), [conditionKey(condition)]: condition });
  }

  function clear(predicate: (condition: RaisedCondition) => boolean): void {
    const current = get(raised);
    const kept = Object.fromEntries(Object.entries(current).filter(([, condition]) => !predicate(condition)));
    if (Object.keys(kept).length !== Object.keys(current).length)
      set(raised, kept);
  }

  return {
    clear,
    conditions,
    raise,
    raised,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useRaisedConditionsStore, import.meta.hot));
