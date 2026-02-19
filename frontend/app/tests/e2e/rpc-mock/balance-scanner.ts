import { createConsola } from 'consola';
import { AbiCoder, type Result } from 'ethers';

const logger = createConsola({ defaults: { tag: 'balance-scanner' } });

const abiCoder = AbiCoder.defaultAbiCoder();

/**
 * Known contract addresses (checksummed).
 */
const BALANCE_SCANNER = '0x54eCF3f6f61F63fdFE7c27Ee8A86e54899600C92';
const MULTICALL = '0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696';

/**
 * Function selectors (first 4 bytes of keccak256 of the signature).
 */
const SEL_TOKENS_BALANCE = '0xb0d861b8'; // tokens_balance(address,address[])
const SEL_ETHER_BALANCES = '0xee1806d2'; // ether_balances(address[])
const SEL_AGGREGATE = '0x252dba42'; // aggregate((address,bytes)[])

/**
 * token balances: account (lowercase) → token (lowercase) → balance bigint
 */
type TokenBalanceMap = Map<string, Map<string, bigint>>;

/**
 * ether balances: address (lowercase) → balance bigint
 */
type EtherBalanceMap = Map<string, bigint>;

/**
 * Stored results for non-balance-scanner sub-calls within aggregates.
 * Key: `${target.toLowerCase()}:${calldata}` → encoded result bytes
 */
type SubCallResultMap = Map<string, string>;

export interface BalanceMaps {
  tokenBalances: TokenBalanceMap;
  etherBalances: EtherBalanceMap;
  subCallResults: SubCallResultMap;
  /** Block number from eth_blockNumber for general use */
  blockNumber: bigint;
  /** Block number extracted from aggregate responses containing balance scanner calls */
  aggregateBlockNumber: bigint;
}

/**
 * Checks whether an eth_call targets a given contract address.
 */
function isCallTo(params: unknown[] | undefined, address: string): boolean {
  if (!params || !params[0])
    return false;
  const call = params[0] as { to?: string };
  return call.to?.toLowerCase() === address.toLowerCase();
}

/**
 * Gets the calldata hex string from eth_call params.
 */
function getCalldata(params: unknown[]): string {
  return (params[0] as { data: string }).data;
}

/**
 * Gets the function selector (first 4 bytes) from calldata.
 */
function getSelector(calldata: string): string {
  return calldata.slice(0, 10).toLowerCase();
}

/**
 * Decodes the ABI-encoded arguments (everything after the 4-byte selector).
 */
function decodeArgs(calldata: string, types: string[]): Result {
  const argsHex = `0x${calldata.slice(10)}`;
  return abiCoder.decode(types, argsHex);
}

/**
 * Decodes an ABI-encoded result.
 */
function decodeResult(data: string, types: string[]): Result {
  return abiCoder.decode(types, data);
}

/**
 * Checks whether an aggregate call contains any balance scanner sub-calls.
 */
function hasBalanceScannerSubCalls(calldata: string): boolean {
  const args = decodeArgs(calldata, ['(address,bytes)[]']);
  const calls: [string, string][] = args[0];
  return calls.some(([target]) => target.toLowerCase() === BALANCE_SCANNER.toLowerCase());
}

/**
 * Builds balance lookup maps by parsing all cassette entries.
 *
 * Balance scanner calls with errors (e.g. "out of gas") are skipped during
 * parsing. At resolve time we always return success with the correct
 * balances — this is more deterministic than replaying transient errors.
 */
export function buildBalanceMaps(cassette: Record<string, { method: string; params?: unknown[]; result?: unknown; error?: unknown }>): BalanceMaps {
  const tokenBalances: TokenBalanceMap = new Map();
  const etherBalances: EtherBalanceMap = new Map();
  const subCallResults: SubCallResultMap = new Map();
  let blockNumber = 0n;
  let aggregateBlockNumber = 0n;

  for (const entry of Object.values(cassette)) {
    if (entry.method !== 'eth_call' || !entry.params || !entry.result)
      continue;

    const calldata = getCalldata(entry.params);
    const selector = getSelector(calldata);

    if (isCallTo(entry.params, BALANCE_SCANNER)) {
      if (selector === SEL_TOKENS_BALANCE) {
        parseTokensBalance(calldata, entry.result as string, tokenBalances);
      }
      else if (selector === SEL_ETHER_BALANCES) {
        parseEtherBalances(calldata, entry.result as string, etherBalances);
      }
    }
    else if (isCallTo(entry.params, MULTICALL) && selector === SEL_AGGREGATE) {
      const aggBlockNumber = parseAggregate(calldata, entry.result as string, tokenBalances, etherBalances, subCallResults);
      if (hasBalanceScannerSubCalls(calldata)) {
        aggregateBlockNumber = aggBlockNumber;
      }
    }
  }

  // Try to get block number from eth_blockNumber entry
  for (const entry of Object.values(cassette)) {
    if (entry.method === 'eth_blockNumber' && entry.result) {
      blockNumber = BigInt(entry.result as string);
      break;
    }
  }

  logger.info(`Built balance maps: ${countTokenEntries(tokenBalances)} token balances, ${etherBalances.size} ether balances, ${subCallResults.size} sub-call results`);
  return { tokenBalances, etherBalances, subCallResults, blockNumber, aggregateBlockNumber };
}

function countTokenEntries(map: TokenBalanceMap): number {
  let count = 0;
  for (const inner of map.values())
    count += inner.size;
  return count;
}

/**
 * Parses a tokens_balance(address, address[]) call and its result,
 * storing non-zero balances into the map.
 */
function parseTokensBalance(calldata: string, result: string, map: TokenBalanceMap): void {
  const args = decodeArgs(calldata, ['address', 'address[]']);
  const account: string = args[0];
  const tokens: string[] = args[1];
  const decoded = decodeResult(result, ['uint256[]']);
  const balances: bigint[] = decoded[0];

  const accountKey = account.toLowerCase();
  let accountMap = map.get(accountKey);
  if (!accountMap) {
    accountMap = new Map();
    map.set(accountKey, accountMap);
  }

  for (const [i, token] of tokens.entries()) {
    const balance = balances[i];
    if (balance !== 0n) {
      accountMap.set(token.toLowerCase(), balance);
    }
  }
}

/**
 * Parses an ether_balances(address[]) call and its result.
 */
function parseEtherBalances(calldata: string, result: string, map: EtherBalanceMap): void {
  const args = decodeArgs(calldata, ['address[]']);
  const addresses: string[] = args[0];
  const decoded = decodeResult(result, ['uint256[]']);
  const balances: bigint[] = decoded[0];

  for (const [i, address] of addresses.entries()) {
    const balance = balances[i];
    if (balance !== 0n) {
      map.set(address.toLowerCase(), balance);
    }
  }
}

/**
 * Parses a multicall aggregate((address,bytes)[]) call, extracting balance
 * scanner sub-calls and parsing their results.
 */
function parseAggregate(
  calldata: string,
  result: string,
  tokenMap: TokenBalanceMap,
  etherMap: EtherBalanceMap,
  subCallMap: SubCallResultMap,
): bigint {
  const args = decodeArgs(calldata, ['(address,bytes)[]']);
  const calls: [string, string][] = args[0];
  const decoded = decodeResult(result, ['uint256', 'bytes[]']);
  const aggBlockNumber: bigint = decoded[0];
  const returnData: string[] = decoded[1];

  for (const [i, [target, subCalldata]] of calls.entries()) {
    const subResult = returnData[i];

    if (target.toLowerCase() === BALANCE_SCANNER.toLowerCase()) {
      const subSelector = getSelector(subCalldata);

      if (subSelector === SEL_TOKENS_BALANCE) {
        parseTokensBalance(subCalldata, subResult, tokenMap);
        continue;
      }
      if (subSelector === SEL_ETHER_BALANCES) {
        parseEtherBalances(subCalldata, subResult, etherMap);
        continue;
      }
    }

    // Store non-balance-scanner sub-call results for replay
    const key = `${target.toLowerCase()}:${subCalldata}`;
    subCallMap.set(key, subResult);
  }

  return aggBlockNumber;
}

/**
 * Checks if a request is a balance scanner eth_call that we can handle semantically.
 * Returns a constructed result hex string, or null if not applicable.
 *
 * Always returns success with correct balances (unknown tokens default to 0).
 * This is more deterministic than replaying transient "out of gas" errors
 * that depend on batch composition.
 */
export function tryResolveBalanceCall(
  method: string,
  params: unknown[] | undefined,
  maps: BalanceMaps,
): string | null {
  if (method !== 'eth_call' || !params)
    return null;

  // Direct balance scanner calls
  if (isCallTo(params, BALANCE_SCANNER)) {
    const calldata = getCalldata(params);
    const selector = getSelector(calldata);

    if (selector === SEL_TOKENS_BALANCE) {
      return resolveTokensBalance(calldata, maps.tokenBalances);
    }
    if (selector === SEL_ETHER_BALANCES) {
      return resolveEtherBalances(calldata, maps.etherBalances);
    }
  }

  // Multicall aggregate — only intercept if it contains balance scanner sub-calls
  if (isCallTo(params, MULTICALL)) {
    const calldata = getCalldata(params);
    const selector = getSelector(calldata);

    if (selector === SEL_AGGREGATE && hasBalanceScannerSubCalls(calldata)) {
      return resolveAggregate(calldata, maps);
    }
  }

  return null;
}

/**
 * Constructs a tokens_balance response for the given calldata using the balance map.
 */
function resolveTokensBalance(calldata: string, map: TokenBalanceMap): string {
  const args = decodeArgs(calldata, ['address', 'address[]']);
  const account: string = args[0];
  const tokens: string[] = args[1];
  const accountKey = account.toLowerCase();
  const accountMap = map.get(accountKey);

  const balances: bigint[] = tokens.map(token => accountMap?.get(token.toLowerCase()) ?? 0n);

  return abiCoder.encode(['uint256[]'], [balances]);
}

/**
 * Constructs an ether_balances response for the given calldata using the balance map.
 */
function resolveEtherBalances(calldata: string, map: EtherBalanceMap): string {
  const args = decodeArgs(calldata, ['address[]']);
  const addresses: string[] = args[0];

  const balances: bigint[] = addresses.map(addr => map.get(addr.toLowerCase()) ?? 0n);

  return abiCoder.encode(['uint256[]'], [balances]);
}

/**
 * Constructs a multicall aggregate response by resolving each sub-call.
 * Sub-calls targeting the balance scanner are resolved semantically.
 * Other sub-calls are looked up from stored results.
 */
function resolveAggregate(calldata: string, maps: BalanceMaps): string {
  const args = decodeArgs(calldata, ['(address,bytes)[]']);
  const calls: [string, string][] = args[0];

  const returnData: string[] = calls.map(([target, subCalldata]) => {
    if (target.toLowerCase() === BALANCE_SCANNER.toLowerCase()) {
      const subSelector = getSelector(subCalldata);

      if (subSelector === SEL_TOKENS_BALANCE) {
        return resolveTokensBalance(subCalldata, maps.tokenBalances);
      }
      if (subSelector === SEL_ETHER_BALANCES) {
        return resolveEtherBalances(subCalldata, maps.etherBalances);
      }
    }

    // Look up stored result for non-balance-scanner sub-calls
    const key = `${target.toLowerCase()}:${subCalldata}`;
    const stored = maps.subCallResults.get(key);
    if (stored) {
      return stored;
    }

    logger.warn(`Aggregate sub-call to unknown target ${target} with selector ${getSelector(subCalldata)}`);
    return '0x';
  });

  return abiCoder.encode(['uint256', 'bytes[]'], [maps.aggregateBlockNumber, returnData]);
}
