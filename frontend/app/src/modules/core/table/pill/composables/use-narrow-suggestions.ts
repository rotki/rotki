import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { AssetsWithId } from '@/modules/assets/types';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { startPromise } from '@shared/utils';
import { assetDisplayCaption, assetDisplayLabel } from '@/modules/core/common/display/assets';
import { useOperatorLabels } from '@/modules/core/table/pill/composables/use-operator-labels';
import { usePillSyntaxHints } from '@/modules/core/table/pill/composables/use-pill-syntax-hints';
import { useRecentFilterValues } from '@/modules/core/table/pill/composables/use-recent-filter-values';
import {
  fieldSuggestions,
  type NarrowSuggestion,
  searchFieldsAndValues,
  syntaxExamples,
} from '@/modules/core/table/pill/core/narrowing';

/** Asset matches offered at once, so a broad query cannot bury the rest of the list. */
const ASSET_RESULT_CAP = 5;

const SEARCH_DEBOUNCE = 300;

interface NarrowSuggestionsReturn {
  /** Field rows before anything is typed, matches after, with any asset results appended. */
  suggestions: ComputedRef<NarrowSuggestion[]>;
  /** An asset search is in flight; the list is usable meanwhile. */
  loading: Readonly<Ref<boolean>>;
  /** Verbatim examples of what can be typed, for the fields currently on offer. */
  examples: ComputedRef<string[]>;
}

/**
 * The bar's narrowing results: the pure cross-field match, plus the asset matches that can only
 * come from the network.
 *
 * An asset field resolves its options remotely, so the pure core cannot offer them and typing
 * `usdc` would only ever surface the Asset *field*, never the asset. Here that search runs
 * debounced against the field's own `searchAsset`, so the composable stays free of any API
 * import and tests can pass a stub field.
 *
 * Asset rows are appended after the synchronous ones rather than merged into their ranking: a
 * result landing mid-keystroke must not renumber the rows the keyboard highlight is pointing at.
 */
export function useNarrowSuggestions(
  query: MaybeRefOrGetter<string>,
  fields: MaybeRefOrGetter<FieldDef[]>,
): NarrowSuggestionsReturn {
  const { recentFor } = useRecentFilterValues();
  const operatorLabels = useOperatorLabels();
  const syntaxHints = usePillSyntaxHints();
  const assetSuggestions = ref<NarrowSuggestion[]>([]);
  const loading = shallowRef<boolean>(false);
  // Only the newest search may publish: an earlier, slower response would otherwise overwrite it.
  let latestRequest = 0;

  function toSuggestions(field: FieldDef, assets: AssetsWithId): NarrowSuggestion[] {
    return assets.slice(0, ASSET_RESULT_CAP).map(asset => ({
      caption: assetDisplayCaption(asset.identifier, asset.name),
      chain: asset.evmChain ?? undefined,
      field,
      kind: 'value' as const,
      // A custom or unknown asset can carry no symbol, and its raw identifier is far too long for
      // a row; it falls back to the shortened address instead.
      label: assetDisplayLabel(asset.identifier, asset.symbol),
      value: asset.identifier,
    }));
  }

  async function searchAssets(): Promise<void> {
    const typed = toValue(query).trim();
    const field = toValue(fields).find(candidate => candidate.searchAsset);

    if (!typed || !field?.searchAsset) {
      set(assetSuggestions, []);
      set(loading, false);
      return;
    }

    const request = ++latestRequest;
    set(loading, true);
    try {
      const found = await field.searchAsset(typed);
      if (request === latestRequest)
        set(assetSuggestions, toSuggestions(field, found));
    }
    catch {
      // A failed search just means no asset rows; the rest of the list still stands.
      if (request === latestRequest)
        set(assetSuggestions, []);
    }
    finally {
      if (request === latestRequest)
        set(loading, false);
    }
  }

  // Immediate, so a bar created with a query already in it (a restored URL, a remounted menu)
  // searches instead of waiting for the next keystroke.
  watchDebounced(() => toValue(query), () => {
    startPromise(searchAssets());
  }, { debounce: SEARCH_DEBOUNCE, immediate: true });

  const suggestions = computed<NarrowSuggestion[]>(() => {
    const available = toValue(fields);
    const typed = toValue(query).trim();
    if (!typed)
      return fieldSuggestions(available);
    const offersAssets = available.some(field => field.searchAsset);
    return [
      ...searchFieldsAndValues(toValue(query), available, get(operatorLabels), undefined, recentFor, get(syntaxHints)),
      ...(offersAssets ? get(assetSuggestions) : []),
    ];
  });

  const examples = computed<string[]>(() => syntaxExamples(toValue(fields), get(syntaxHints)));

  return { examples, loading: readonly(loading), suggestions };
}
