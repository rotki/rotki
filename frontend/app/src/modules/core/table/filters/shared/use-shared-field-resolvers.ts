import type { ParseTimestamp } from '@/modules/core/table/pill/core/typed-filters';
import { toHumanReadable } from '@rotki/common';
import { NO_COLLECTION_RESOLVE, useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { dateBoundParser, dateDeserializer } from '@/modules/core/common/data/date';
import { capitalizeAcronyms } from '@/modules/core/common/display/acronyms';
import { assetDisplayLabel } from '@/modules/core/common/display/assets';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useLocations } from '@/modules/core/common/use-locations';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import { useScramble } from '@/modules/settings/use-scramble';
import { useSetting } from '@/modules/settings/use-setting';

/**
 * How a shared field turns its raw wire values into what the pill and the option list show.
 *
 * Every table filtering on an asset, a location, a protocol or an address needs exactly the same
 * answers, and each one is a small trap of its own: an asset must not resolve through its
 * collection, an address must be scrambled before it is shown, a protocol id is not its label. So
 * they are answered once here rather than per table.
 */
export interface SharedFieldResolvers {
  /** Maps a raw location id such as `polygon_pos` to its display name, `Polygon PoS`. */
  readonly resolveLocationName: (value: string) => string;
  /** Maps a raw chain id such as `optimism` to its display name, `Optimism`. */
  readonly resolveChainName: (value: string) => string;
  /** Maps a raw counterparty id such as `uniswap-v2` to its display label, `Uniswap V2`. */
  readonly resolveProtocolName: (value: string) => string;
  /** Maps an asset identifier to its symbol, or to a shortened address when it has no metadata. */
  readonly resolveAssetSymbol: (value: string) => string;
  /** Maps an asset identifier to its chain, such as `base`, shown as an icon beside the symbol. */
  readonly resolveAssetChain: (value: string) => string | undefined;
  /** Maps an address or transaction hash to the short, privacy-respecting form shown on a pill. */
  readonly resolveHex: (value: string) => string;
  /** Maps a machine token that is already spaced words, `evm event`, to its display casing. */
  readonly resolveTokenName: (value: string) => string;
  /** Formats a unix-second timestamp as a date in the user's configured format. */
  readonly formatDate: (value: string) => string;
  /** The inverse: parses a written date into the unix-second bound a filter stores. */
  readonly parseDate: ParseTimestamp;
}

/**
 * The display resolution every pill-bar table shares, in one place so a fix lands once.
 *
 * Vue-layer on purpose: these read stores and user settings. The field definitions built from them
 * stay pure, which is what keeps the field factories testable without mounting anything.
 */
export function useSharedFieldResolvers(): SharedFieldResolvers {
  const { getLocationData } = useLocations();
  const { getChainName } = useSupportedChains();
  const { getCounterpartyData } = useHistoryEventCounterpartyMappings();
  const { getAssetField, getAssetInfo } = useAssetInfoRetrieval();
  const { scrambleAddress } = useScramble();
  const dateInputFormat = useSetting('dateInputFormat');

  const resolveLocationName = (value: string): string => getLocationData(value)?.name ?? value;

  const resolveProtocolName = (value: string): string =>
    toHumanReadable(get(getCounterpartyData(value)).label, 'sentence');

  const resolveAssetSymbol = (value: string): string =>
    assetDisplayLabel(value, getAssetField(value, 'symbol', NO_COLLECTION_RESOLVE));

  const resolveAssetChain = (value: string): string | undefined =>
    getAssetInfo(value, NO_COLLECTION_RESOLVE)?.evmChain ?? undefined;

  const resolveHex = (value: string): string => truncateAddress(scrambleAddress(value), 4);

  /**
   * Renders a snake-cased identifier as a display label.
   *
   * @remarks
   * Sentence casing on its own lowercases acronyms, giving `Evm event` and `Eth withdrawal event`,
   * so the acronyms are restored afterwards.
   */
  const resolveTokenName = (value: string): string => capitalizeAcronyms(toHumanReadable(value, 'sentence'));

  return {
    formatDate: dateDeserializer(dateInputFormat),
    parseDate: dateBoundParser(dateInputFormat),
    resolveAssetChain,
    resolveAssetSymbol,
    resolveChainName: getChainName,
    resolveHex,
    resolveLocationName,
    resolveProtocolName,
    resolveTokenName,
  };
}
