import type { SupportedAsset, Writeable } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { AssetUpdateConflictResult, ConflictResolution } from '@/modules/assets/types';
import type { ConflictResolutionStrategy } from '@/modules/core/common/common-types';
import { objectKeys } from '@/modules/core/common/data/array';
import { uniqueObjects, uniqueStrings } from '@/modules/core/common/data/data';

type AssetKey = keyof SupportedAsset;

/** Which of the two bulk buttons reads as pressed. */
interface StrategyForAll {
  local: boolean;
  remote: boolean;
}

interface UseAssetConflictResolutionReturn {
  /** Whether the per-asset table is showing rather than the two bulk choices. */
  manualResolution: Readonly<Ref<boolean>>;
  /** The strategy chosen per asset identifier; each row binds one entry with `v-model`. */
  modelResolution: Ref<ConflictResolution>;
  /** Whether every conflict has been given a strategy, which is what enables confirming. */
  valid: ComputedRef<boolean>;
  /** Whether anything has been chosen yet, which is when the dialog stops being dismissable. */
  hasResolution: ComputedRef<boolean>;
  /** How many distinct assets are still without a strategy. */
  remaining: ComputedRef<number>;
  /** Whether the same identifier arrived more than once, which the dialog warns about. */
  warnDuplicate: ComputedRef<boolean>;
  /** The identifiers that arrived more than once, named in the warning. */
  duplicateIdentifiers: ComputedRef<string[]>;
  /** Which bulk button is pressed, which is none once a row has been changed by hand. */
  activeStrategyForAll: ComputedRef<StrategyForAll>;
  /** Applies one strategy to every conflict. */
  setResolution: (strategy: ConflictResolutionStrategy) => void;
  /** Re-reads the bulk selection after a single row changed. */
  onStrategyChange: (strategy?: ConflictResolutionStrategy) => void;
  /** Switches to resolving each asset by hand. */
  enableManualResolution: () => void;
}

/**
 * The fields worth showing for a conflict: every key either side has a value for.
 *
 * @remarks
 * A key absent from one side is still shown, so the row makes the difference visible rather than
 * hiding it; only a key null on both sides drops out.
 *
 * @param conflict - the asset as it exists locally and remotely
 * @returns the keys to render, remote order first
 */
export function getConflictFields(conflict: AssetUpdateConflictResult): AssetKey[] {
  function nonNull(key: AssetKey, asset: SupportedAsset): boolean {
    return asset[key] !== null;
  }
  const remote = objectKeys(conflict.remote).filter(key => nonNull(key, conflict.remote));
  const local = objectKeys(conflict.local).filter(key => nonNull(key, conflict.local));
  return [...remote, ...local].filter(uniqueStrings);
}

/**
 * Whether the two sides disagree on a field, which is what the row highlights.
 *
 * @param conflict - the asset as it exists locally and remotely
 * @param field - the key being compared
 * @returns whether the values differ
 */
export function isDiff(conflict: AssetUpdateConflictResult, field: AssetKey): boolean {
  return conflict.local[field] !== conflict.remote[field];
}

/**
 * Owns which strategy each conflicting asset is being resolved with, and the rules the dialog
 * draws from it: whether it can be confirmed, how many assets are left, and whether the update
 * sent the same identifier twice.
 *
 * @param conflicts - the conflicting assets, as the update reported them
 * @returns the resolution state and the ways it changes
 */
export function useAssetConflictResolution(
  conflicts: MaybeRefOrGetter<AssetUpdateConflictResult[]>,
): UseAssetConflictResolutionReturn {
  const manualResolution = shallowRef<boolean>(false);
  const modelResolution = ref<ConflictResolution>({});
  const strategyModeForAll = shallowRef<ConflictResolutionStrategy>();

  const identifiers = computed<string[]>(() => toValue(conflicts).map(({ identifier }) => identifier));

  const resolutionLength = computed<number>(() => Object.keys(get(modelResolution)).length);

  const hasResolution = computed<boolean>(() => get(resolutionLength) > 0);

  const activeStrategyForAll = computed<StrategyForAll>(() => {
    const all = toValue(conflicts);
    if (all.length === 0 || get(resolutionLength) !== all.length)
      return { local: false, remote: false };

    const strategy = get(strategyModeForAll);
    return { local: strategy === 'local', remote: strategy === 'remote' };
  });

  const remaining = computed<number>(() =>
    uniqueObjects(toValue(conflicts), ({ identifier }) => identifier).length - get(resolutionLength),
  );

  const duplicateIdentifiers = computed<string[]>(() =>
    [...get(identifiers)].sort().filter((identifier, index, all) => all.indexOf(identifier) !== index),
  );

  const warnDuplicate = computed<boolean>(() => get(duplicateIdentifiers).length > 0);

  const valid = computed<boolean>(() => {
    const expected = [...get(identifiers)].filter(uniqueStrings).sort();
    const resolved = Object.keys(get(modelResolution)).sort();
    return expected.length === resolved.length && expected.every((identifier, index) => identifier === resolved[index]);
  });

  function setResolution(strategy: ConflictResolutionStrategy): void {
    const resolutionStrategy: Writeable<ConflictResolution> = {};
    for (const identifier of get(identifiers))
      resolutionStrategy[identifier] = strategy;

    set(modelResolution, resolutionStrategy);
    set(strategyModeForAll, strategy);
  }

  function onStrategyChange(strategy?: ConflictResolutionStrategy): void {
    const uniform = Object.values(get(modelResolution)).every(chosen => chosen === strategy);
    set(strategyModeForAll, uniform ? strategy : undefined);
  }

  function enableManualResolution(): void {
    set(manualResolution, true);
  }

  return {
    activeStrategyForAll,
    duplicateIdentifiers,
    enableManualResolution,
    hasResolution,
    manualResolution: readonly(manualResolution),
    modelResolution,
    onStrategyChange,
    remaining,
    setResolution,
    valid,
    warnDuplicate,
  };
}
