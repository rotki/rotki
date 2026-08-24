import type { MaybeRefOrGetter, Ref } from 'vue';
import { isValidEthAddress, type SupportedAsset } from '@rotki/common';
import { pick } from 'es-toolkit';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface ManagedTokenLookupOptions {
  /** The asset the form is editing. The looked-up details are written back into it. */
  readonly asset: Ref<SupportedAsset>;
  /** The address to look up, as the form holds it. */
  readonly address: MaybeRefOrGetter<string>;
  /** The chain to look it up on. A chain with no transaction support is not looked up at all. */
  readonly evmChain: MaybeRefOrGetter<string | null | undefined>;
  /** Called with the fields the lookup filled in, so their stale errors can be cleared. */
  readonly onFilled: (fields: Array<keyof SupportedAsset>) => void;
}

interface ManagedTokenLookupReturn {
  /** True while a lookup is in flight. The address and chain inputs disable on it. */
  readonly fetching: Readonly<Ref<boolean>>;
  /** Looks the token up now, for the button that asks for it. */
  readonly refreshTokenData: () => Promise<void>;
  /** Suppresses the next automatic lookup. An opened edit dialog does not re-fetch what it loaded. */
  readonly suppressNextLookup: () => void;
}

const FILLED_FIELDS = ['decimals', 'name', 'symbol'] as const;

/**
 * What the lookup found, or what the form already had.
 *
 * A contract that does not answer for a field reports it as null, which the response type does not
 * admit but the backend documents and returns, so it is checked for at runtime rather than trusted
 * away. An empty string and a zero mean the same thing here, which does leave a genuine
 * zero-decimal token showing whatever the form had, as it always has.
 */
function looked<T extends string | number>(
  found: T | null | undefined,
  current: T | null | undefined,
): T | null | undefined {
  if (found === undefined || found === null || found === '' || found === 0)
    return current;

  return found;
}

/**
 * Fills a token's name, symbol and decimals from the chain.
 *
 * The lookup runs on its own whenever the address and chain together name a real token, which is
 * what makes adding one a matter of pasting an address. It is deliberately additive: a field the
 * chain has nothing for keeps what the user typed, so a lookup never empties the form.
 */
export function useManagedTokenLookup(options: ManagedTokenLookupOptions): ManagedTokenLookupReturn {
  const { address, asset, evmChain, onFilled } = options;

  const fetching = shallowRef<boolean>(false);
  const skipNext = shallowRef<boolean>(false);

  const { fetchTokenDetails } = useAssetInfoRetrieval();
  const { txEvmChains } = useSupportedChains();

  function isSupportedChain(chain: string): boolean {
    return get(txEvmChains).some(({ evmChainName }) => evmChainName === chain);
  }

  async function fetchTokenData(tokenAddress: string, chain: string): Promise<void> {
    if (!isSupportedChain(chain))
      return;

    set(fetching, true);
    try {
      const details = await fetchTokenDetails({ address: tokenAddress, evmChain: chain });
      // Read after the request, not before: the user goes on typing while it is in flight, and a
      // copy taken beforehand would put the older value back.
      const current = pick(get(asset), FILLED_FIELDS);

      set(asset, {
        ...get(asset),
        decimals: looked(details.decimals, current.decimals),
        name: looked(details.name, current.name),
        symbol: looked(details.symbol, current.symbol),
      });
      onFilled([...FILLED_FIELDS]);
    }
    finally {
      // Always re-enable the fields, even if the lookup throws, so the form never stays locked.
      set(fetching, false);
    }
  }

  async function refreshTokenData(): Promise<void> {
    const chain = toValue(evmChain);
    if (!chain)
      return;

    await fetchTokenData(toValue(address), chain);
  }

  function suppressNextLookup(): void {
    set(skipNext, true);
  }

  const watched: [() => string, () => string | null | undefined] = [
    (): string => toValue(address),
    (): string | null | undefined => toValue(evmChain),
  ];

  watch(watched, async ([tokenAddress, chain]): Promise<void> => {
    if (!chain)
      return;

    // A suppressed run still counts as the run it suppresses, so the next edit looks up normally.
    if (get(skipNext) || !isValidEthAddress(tokenAddress)) {
      set(skipNext, false);
      return;
    }

    await fetchTokenData(tokenAddress, chain);
  });

  return {
    fetching: readonly(fetching),
    refreshTokenData,
    suppressNextLookup,
  };
}
