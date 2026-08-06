import { startPromise } from '@shared/utils';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { DisplayKinds, type ValueDisplay } from '@/modules/core/table/pill/core/types';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import { useHistoryStore } from '@/modules/history/use-history-store';
import { useLocationLabels } from '@/modules/history/use-location-labels';
import { useScramble } from '@/modules/settings/use-scramble';

/** What one account offers the pill: how it reads, and what finds it while narrowing. */
interface AccountOption {
  /** The tracked/ENS name, absent when the account has none. */
  readonly name?: string;
  /**
   * Whether the value is an address on a chain, and so must be shortened and scrambled. A
   * `locationLabel` on an exchange is an account *name* the user chose (`Kraken 1`), which the
   * table itself never scrambles — cf. `HistoryEventAccount`'s `no-scramble`.
   */
  readonly isAddress: boolean;
  /** Whether the name is still being resolved, drawn as a skeleton row rather than a flash. */
  readonly pending: boolean;
  readonly tags: string[];
  /** Where the account is held (`ethereum`, `kraken`), which an exchange row draws its icon from. */
  readonly location: string;
}

export interface DataIssueAccountOptions {
  readonly suggest: () => string[];
  readonly resolveLabel: (value: string) => string;
  readonly resolveCaption: (value: string) => string | undefined;
  readonly resolveKeywords: (value: string) => string | undefined;
  readonly resolveLoading: (value: string) => boolean;
  readonly resolveDisplay: (value: string) => ValueDisplay | undefined;
}

/**
 * The option list for the data issues account pill: every `(location, locationLabel)` pair the
 * user's history has, which is exactly the domain a data issue's account is drawn from, and the
 * same list history's own account pill picks from.
 *
 * The list is not part of the issues response, so it is fetched once when the bar is first built;
 * repeated calls join the one in-flight request.
 */
export function useDataIssueAccountOptions(): DataIssueAccountOptions {
  const { locationLabels } = storeToRefs(useHistoryStore());
  const { fetchLocationLabels } = useHistoryDataFetching();
  const { getAccountName, getBlockchainLocation, getTags, isAccountNamePending } = useLocationLabels(() => undefined);
  const { scrambleAddress } = useScramble();

  onMounted(() => {
    if (get(locationLabels).length === 0)
      startPromise(fetchLocationLabels());
  });

  // One pass over the list rather than a lookup per call: a resolver runs once per candidate value
  // on every keystroke while the bar narrows.
  const byLabel = computed<Map<string, AccountOption>>(() => {
    const map = new Map<string, AccountOption>();
    for (const item of get(locationLabels)) {
      if (map.has(item.locationLabel))
        continue;
      map.set(item.locationLabel, {
        isAddress: getBlockchainLocation(item.location) !== undefined,
        location: item.location,
        name: getAccountName(item),
        pending: isAccountNamePending(item),
        tags: getTags(item),
      });
    }
    return map;
  });

  const values = computed<string[]>(() => [...get(byLabel).keys()]);

  /** An address is shortened and scrambled; an exchange account name is shown as it is. */
  function shorten(value: string, option: AccountOption | undefined): string {
    return option?.isAddress === false ? value : truncateAddress(scrambleAddress(value), 4);
  }

  function resolveLabel(value: string): string {
    const option = get(byLabel).get(value);
    return option?.name ?? shorten(value, option);
  }

  function resolveCaption(value: string): string | undefined {
    // Shown muted under a name. With no name the label is the value itself, so a caption would
    // only repeat it.
    const option = get(byLabel).get(value);
    return option?.name ? shorten(value, option) : undefined;
  }

  function resolveKeywords(value: string): string | undefined {
    const option = get(byLabel).get(value);
    if (!option)
      return undefined;
    // The row shows a name or a shortened, scrambled address, so neither a full address nor a
    // typed name would match what is drawn without these.
    return [value, option.name, ...option.tags].filter(Boolean).join(' ');
  }

  function resolveLoading(value: string): boolean {
    return get(byLabel).get(value)?.pending ?? false;
  }

  /**
   * Every row in the table carries a mark, so every row here does too: a blockie for an address,
   * the exchange's own logo for an account held there — drawn from the location, since the value
   * is the account's name.
   */
  function resolveDisplay(value: string): ValueDisplay | undefined {
    const option = get(byLabel).get(value);
    if (!option)
      return undefined;
    return option.isAddress
      ? { kind: DisplayKinds.ADDRESS }
      : { kind: DisplayKinds.LOCATION, source: option.location };
  }

  return {
    resolveCaption,
    resolveDisplay,
    resolveKeywords,
    resolveLabel,
    resolveLoading,
    suggest: (): string[] => get(values),
  };
}
