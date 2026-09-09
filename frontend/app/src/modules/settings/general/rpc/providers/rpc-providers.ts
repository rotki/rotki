import { Blockchain } from '@rotki/common';

export const RPC_PROVIDER_IDS = ['infura', 'alchemy', 'quicknode'] as const;

export type RpcProviderId = typeof RPC_PROVIDER_IDS[number];

interface RpcProviderCredentials {
  /** The api key or token the endpoint authenticates with. */
  key: string;
  /** The per-endpoint subdomain QuickNode puts in front of the network, absent for the others. */
  endpointName?: string;
}

export interface RpcProviderMatch {
  credentials: RpcProviderCredentials;
  /** The rotki chain the endpoint points at, absent when the network is not one rotki supports. */
  chain?: string;
  providerId: RpcProviderId;
}

/**
 * What the user may have to do on the provider's own side before the other networks answer.
 *
 * @remarks
 * The three differ, which is what the issue asked to establish: Infura keys carry a per-network
 * switch that is on by default, so a refusal there means that one network was turned off for the
 * key; a QuickNode endpoint serves other networks only once Multichain is enabled on it; an
 * Alchemy app is issued one key for every network and needs nothing.
 */
type RpcProviderEnablement = 'multichain-endpoint' | 'none' | 'per-network';

export interface RpcProvider {
  /** rotki chain ids this provider serves, in the order the tables declare them. */
  chains: string[];
  enablement: RpcProviderEnablement;
  id: RpcProviderId;
  name: string;
}

interface RpcProviderDefinition extends Omit<RpcProvider, 'chains'> {
  /** Builds the endpoint this provider serves `network` on. */
  build: (network: string, credentials: RpcProviderCredentials) => string;
  /**
   * rotki chain id to the provider's own network slug.
   *
   * @remarks
   * Slugs are not derivable from rotki's chain ids and each provider names its networks its own
   * way, so every entry is copied from that provider's own documentation and carries the date it
   * was read. A chain the provider is not confirmed to serve is left out rather than guessed: an
   * absent entry is simply not offered, while a wrong one tells the user their key failed when it
   * was the url that was wrong.
   */
  networks: Record<string, string>;
  /** Reads the network slug and the credentials out of one of this provider's urls. */
  parse: (url: URL) => { credentials: RpcProviderCredentials; network: string } | undefined;
  /** Whether a url is served by this provider at all, whatever its network. */
  owns: (url: URL) => boolean;
}

/**
 * The subdomain in front of `suffix`, or undefined when the host is not under it.
 *
 * @remarks
 * Returns the whole prefix, dots included, so a caller that expects a single label has to check.
 * `sub('a.b.infura.io', 'infura.io')` is `'a.b'`, and `sub('infura.io', 'infura.io')` is undefined.
 */
function sub(hostname: string, suffix: string): string | undefined {
  const host = hostname.toLowerCase();
  const dotted = `.${suffix}`;
  if (!host.endsWith(dotted))
    return undefined;

  const prefix = host.slice(0, -dotted.length);
  return prefix.length > 0 ? prefix : undefined;
}

/** The non-empty segments of a path, so a trailing slash never becomes an empty token. */
function segments(pathname: string): string[] {
  return pathname.split('/').filter(segment => segment.length > 0);
}

/** The key from a `/<prefix>/<key>` path, rejecting anything longer or differently shaped. */
function keyAfter(pathname: string, prefix: string): string | undefined {
  const parts = segments(pathname);
  return parts.length === 2 && parts[0] === prefix ? parts[1] : undefined;
}

/**
 * QuickNode addresses ethereum mainnet without a network segment, so the empty slug is a real
 * network rather than a missing one.
 */
const QUICKNODE_ETHEREUM = '';

const definitions: Record<RpcProviderId, RpcProviderDefinition> = {
  alchemy: {
    build: (network, { key }) => `https://${network}.g.alchemy.com/v2/${key}`,
    enablement: 'none',
    id: 'alchemy',
    name: 'Alchemy',
    /** From the `Network` enum the Alchemy SDK builds its own urls from, read 2026-09-08. */
    networks: {
      [Blockchain.ARBITRUM_ONE]: 'arb-mainnet',
      [Blockchain.BASE]: 'base-mainnet',
      [Blockchain.BSC]: 'bnb-mainnet',
      [Blockchain.ETH]: 'eth-mainnet',
      [Blockchain.GNOSIS]: 'gnosis-mainnet',
      [Blockchain.HYPERLIQUID]: 'hyperliquid-mainnet',
      [Blockchain.INK]: 'ink-mainnet',
      [Blockchain.OPTIMISM]: 'opt-mainnet',
      [Blockchain.POLYGON_POS]: 'polygon-mainnet',
      [Blockchain.SCROLL]: 'scroll-mainnet',
      [Blockchain.SOLANA]: 'solana-mainnet',
      [Blockchain.SONIC]: 'sonic-mainnet',
    },
    owns: url => sub(url.hostname, 'g.alchemy.com') !== undefined,
    parse(url) {
      const network = sub(url.hostname, 'g.alchemy.com');
      const key = keyAfter(url.pathname, 'v2');
      if (network === undefined || network.includes('.') || key === undefined)
        return undefined;

      return { credentials: { key }, network };
    },
  },
  infura: {
    build: (network, { key }) => `https://${network}.infura.io/v3/${key}`,
    enablement: 'per-network',
    id: 'infura',
    name: 'Infura',
    /**
     * From the endpoint table at docs.infura.io, read 2026-09-08.
     *
     * @remarks
     * Gnosis, Sonic and Ink are absent from that table, so they are not offered. Hyperliquid is
     * served under Infura's own name for it, HyperEVM, which is the same chain id rotki uses.
     */
    networks: {
      [Blockchain.ARBITRUM_ONE]: 'arbitrum-mainnet',
      [Blockchain.BASE]: 'base-mainnet',
      [Blockchain.BSC]: 'bsc-mainnet',
      [Blockchain.ETH]: 'mainnet',
      [Blockchain.HYPERLIQUID]: 'hyperevm-mainnet',
      [Blockchain.MONAD]: 'monad-mainnet',
      [Blockchain.OPTIMISM]: 'optimism-mainnet',
      [Blockchain.POLYGON_POS]: 'polygon-mainnet',
      [Blockchain.SCROLL]: 'scroll-mainnet',
      [Blockchain.SOLANA]: 'solana-mainnet',
    },
    owns: url => sub(url.hostname, 'infura.io') !== undefined,
    parse(url) {
      const network = sub(url.hostname, 'infura.io');
      const key = keyAfter(url.pathname, 'v3');
      if (network === undefined || network.includes('.') || key === undefined)
        return undefined;

      return { credentials: { key }, network };
    },
  },
  quicknode: {
    build: (network, { endpointName, key }) => network === QUICKNODE_ETHEREUM
      ? `https://${endpointName}.quiknode.pro/${key}/`
      : `https://${endpointName}.${network}.quiknode.pro/${key}/`,
    enablement: 'multichain-endpoint',
    id: 'quicknode',
    name: 'QuickNode',
    /**
     * From the `docs-demo.<network>.quiknode.pro` host in each chain's own `eth_chainId` page,
     * read 2026-09-08, with the chain id in the sample response checked against rotki's.
     *
     * @remarks
     * Ink is left out because those pages only document `ink-sepolia`, and Hyperliquid because
     * QuickNode serves it at `hype-mainnet` with an `/evm` path segment that this url shape cannot
     * express. Both would build an endpoint that cannot answer.
     */
    networks: {
      [Blockchain.ARBITRUM_ONE]: 'arbitrum-mainnet',
      [Blockchain.BASE]: 'base-mainnet',
      [Blockchain.BSC]: 'bsc',
      [Blockchain.ETH]: QUICKNODE_ETHEREUM,
      [Blockchain.GNOSIS]: 'xdai',
      [Blockchain.MONAD]: 'monad-mainnet',
      [Blockchain.OPTIMISM]: 'optimism',
      [Blockchain.POLYGON_POS]: 'matic',
      [Blockchain.SCROLL]: 'scroll-mainnet',
      [Blockchain.SOLANA]: 'solana-mainnet',
      [Blockchain.SONIC]: 'sonic-mainnet',
    },
    owns: url => sub(url.hostname, 'quiknode.pro') !== undefined,
    parse(url) {
      const prefix = sub(url.hostname, 'quiknode.pro');
      const parts = segments(url.pathname);
      if (prefix === undefined || parts.length !== 1)
        return undefined;

      const labels = prefix.split('.');
      if (labels.length > 2)
        return undefined;

      const [endpointName, network = QUICKNODE_ETHEREUM] = labels;
      return { credentials: { endpointName, key: parts[0] }, network };
    },
  },
};

function toUrl(endpoint: string): URL | undefined {
  try {
    const url = new URL(endpoint.trim());
    return url.protocol === 'https:' || url.protocol === 'http:' ? url : undefined;
  }
  catch {
    return undefined;
  }
}

function chainOfNetwork(definition: RpcProviderDefinition, network: string): string | undefined {
  return Object.entries(definition.networks).find(([, slug]) => slug === network)?.[0];
}

/** The provider, without the parsing internals the ui has no business touching. */
export function getRpcProvider(id: RpcProviderId): RpcProvider {
  const { networks, ...provider } = definitions[id];
  return { ...provider, chains: Object.keys(networks) };
}

/**
 * Recognises one of the known providers from a pasted endpoint.
 *
 * @remarks
 * Returns undefined on anything it is not sure about, since the caller turns a match into a set of
 * urls it will write to the user's node list. A url whose host is the provider's but whose network
 * rotki does not support still matches, with no `chain`: the key is usable, that one chain is not.
 */
export function detectRpcProvider(endpoint: string): RpcProviderMatch | undefined {
  const url = toUrl(endpoint);
  if (!url)
    return undefined;

  for (const definition of Object.values(definitions)) {
    const parsed = definition.parse(url);
    if (!parsed)
      continue;

    return {
      chain: chainOfNetwork(definition, parsed.network),
      credentials: parsed.credentials,
      providerId: definition.id,
    };
  }

  return undefined;
}

/** The endpoint a match's credentials address `chain` on, or undefined when it does not serve it. */
export function buildRpcEndpoint(match: RpcProviderMatch, chain: string): string | undefined {
  const definition = definitions[match.providerId];
  const network = definition.networks[chain];
  return network === undefined ? undefined : definition.build(network, match.credentials);
}

/** Whether an endpoint is served by a provider, used to spot nodes a chain already has. */
export function isRpcProviderEndpoint(endpoint: string, id: RpcProviderId): boolean {
  const url = toUrl(endpoint);
  return !!url && definitions[id].owns(url);
}

/** The credential with its middle hidden, so a shared screen never shows a whole key. */
export function maskRpcKey(key: string): string {
  return key.length <= 10 ? '…' : `${key.slice(0, 4)}…${key.slice(-4)}`;
}

/**
 * Text with every occurrence of the credential masked.
 *
 * @remarks
 * Used on the endpoints a list repeats, and on the backend's own failure messages, which quote the
 * endpoint more than once and would otherwise put the whole key on screen.
 */
export function maskRpcEndpoint(text: string, key: string): string {
  return key.length > 0 ? text.replaceAll(key, maskRpcKey(key)) : text;
}
