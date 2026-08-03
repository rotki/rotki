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
  /** Raw location id (e.g. `polygon_pos`) -> its display name (e.g. `Polygon PoS`). */
  readonly resolveLocationName: (value: string) => string;
  /** Raw chain id (e.g. `optimism`) -> its display name (e.g. `Optimism`). */
  readonly resolveChainName: (value: string) => string;
  /** Raw counterparty id (e.g. `uniswap-v2`) -> its display label (e.g. `Uniswap V2`). */
  readonly resolveProtocolName: (value: string) => string;
  /** Asset identifier -> its symbol, or a shortened address when it has no metadata. */
  readonly resolveAssetSymbol: (value: string) => string;
  /** Asset identifier -> its chain (e.g. `base`), shown as a chain icon beside the symbol. */
  readonly resolveAssetChain: (value: string) => string | undefined;
  /** An address or transaction hash -> the short, privacy-respecting form shown on a pill. */
  readonly resolveHex: (value: string) => string;
  /** A machine token that is already spaced words (`evm event`) -> its display casing. */
  readonly resolveTokenName: (value: string) => string;
  /** Unix-second timestamp -> a human date in the user's configured format. */
  readonly formatDate: (value: string) => string;
  /** The inverse: a written date -> the unix-second bound a filter stores. */
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

  // Both asset resolvers deliberately skip the collection parent. Asset info walks up to an asset's
  // collection by default, which is right where the collection is what is meant (a balance row
  // aggregating every DAI) but wrong on a filter pill: the filter targets one exact identifier, so
  // a pill for XDAI on Gnosis read "DAI", the collection's symbol, while the editor's list, which
  // reads the search result directly, said XDAI. The chain has the same problem.
  //
  // An asset with no info, unknown or simply not resolved yet, has no symbol, and its raw
  // identifier is far too long for a pill: `eip155:1/erc20:0x214A…` swamped the whole bar. It falls
  // back to the shortened contract address, which is how rotki shows any unnamed address anyway.
  const resolveAssetSymbol = (value: string): string =>
    assetDisplayLabel(value, getAssetField(value, 'symbol', NO_COLLECTION_RESOLVE));

  const resolveAssetChain = (value: string): string | undefined =>
    getAssetInfo(value, NO_COLLECTION_RESOLVE)?.evmChain ?? undefined;

  const resolveHex = (value: string): string => truncateAddress(scrambleAddress(value), 4);

  // Sentence-casing alone lowercases acronyms into `Evm event` / `Eth withdrawal event`.
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
