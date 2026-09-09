export const RPC_CONNECT_ERROR = {
  REJECTED: 'rejected',
  UNKNOWN: 'unknown',
  UNREACHABLE: 'unreachable',
  WRONG_NETWORK: 'wrong-network',
} as const;

export type RpcConnectError = typeof RPC_CONNECT_ERROR[keyof typeof RPC_CONNECT_ERROR];

/**
 * Ordered because a message can match more than one pattern.
 *
 * @remarks
 * "Failed to connect … due to 401" is both a connection failure and a rejected key, and the key is
 * the half the user can act on, so the credential patterns are tested first.
 */
const patterns: [RpcConnectError, RegExp][] = [
  [RPC_CONNECT_ERROR.REJECTED, /\b401\b|\b403\b|unauthori[sz]ed|forbidden|invalid (?:api )?key/i],
  [RPC_CONNECT_ERROR.WRONG_NETWORK, /right network|network id|chain id|unexpected node version/i],
  [RPC_CONNECT_ERROR.UNREACHABLE, /failed to connect|connection|timed? ?out|unreachable|resolve/i],
];

/**
 * Classifies a backend connect failure into something a list row can say in three words.
 *
 * @param message - the backend's own message, which the caller still shows in full on demand
 * @returns the kind of failure, or `unknown` when nothing matches
 */
export function summariseRpcConnectError(message: string): RpcConnectError {
  return patterns.find(([, pattern]) => pattern.test(message))?.[0] ?? RPC_CONNECT_ERROR.UNKNOWN;
}

/** The `NodeName(name=…, owned=True, blockchain=<…>)` repr, which holds no parentheses of its own. */
const NODE_REPR = /\s*NodeName\([^()]*\)/g;

/** The chain the message names, which the row it sits under already carries. */
const CHAIN_IN_LEAD = /^(Failed to connect) to \S+ node\b/i;

/** An endpoint, with the phrase that introduces it when there is one. */
const ENDPOINT = /(?:\s+(?:at endpoint|for url:))?\s+(https?:\/\/\S+)/gi;

/**
 * Rewrites a backend connect failure into something worth reading in a list row.
 *
 * @remarks
 * The backend answers with a Python repr of the node and then quotes the endpoint a second time, so
 * one failure costs three wrapped lines that are mostly internals. Each rewrite is conditional on
 * its own pattern and none of them invent text, so a message that does not have this shape is
 * passed through untouched. Drop this once the backend's own message is fixed.
 *
 * @param message - the backend's own message, with the credential already masked
 * @returns the message without the repr, the chain it names twice, and the repeated endpoint
 */
export function tidyRpcConnectMessage(message: string): string {
  const seen = new Set<string>();

  return message
    .replace(NODE_REPR, '')
    .replace(CHAIN_IN_LEAD, '$1')
    .replace(ENDPOINT, (match, url: string) => {
      if (seen.has(url))
        return '';

      seen.add(url);
      return match;
    })
    .replace(/\s{2,}/g, ' ')
    .trim();
}
