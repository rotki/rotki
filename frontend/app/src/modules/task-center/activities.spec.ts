import { describe, expect, it } from 'vitest';
import { type ActivityId, ActivityPart, activityParts } from '@/modules/task-center/core/types';

/**
 * Every activity descriptor, found rather than registered, the same way `flows.spec.ts` finds flows.
 *
 * Descriptors live beside their producers as `*.activity.ts`, so nothing enumerates them at
 * runtime; the glob does, at test time only, without a registry that would import every producer.
 */
const modules = import.meta.glob<Record<string, unknown>>('@/modules/**/*.activity.ts', { eager: true });

/** The runtime surface of a descriptor, which is all this spec calls. */
interface Descriptor {
  readonly kind: string;
  readonly id: (subject: unknown) => ActivityId;
  readonly partsOf: (subject: unknown) => readonly (string | number)[];
  readonly batchId: (prefix: readonly []) => ActivityId;
}

interface Declared {
  readonly file: string;
  readonly name: string;
  readonly descriptor: Descriptor;
}

function isDescriptor(value: unknown): value is Descriptor {
  if (typeof value !== 'object' || value === null)
    return false;

  return 'kind' in value && typeof value.kind === 'string'
    && 'id' in value && typeof value.id === 'function'
    && 'partsOf' in value && typeof value.partsOf === 'function'
    && 'batchId' in value && typeof value.batchId === 'function';
}

const declared: Declared[] = Object.entries(modules).flatMap(([file, exported]) =>
  Object.entries(exported)
    .filter((entry): entry is [string, Descriptor] => isDescriptor(entry[1]))
    .map(([name, descriptor]) => ({ descriptor, file, name })),
);

const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

/**
 * Realistic subjects per descriptor, by export name.
 *
 * Keyed by name rather than imported, so this spec does not grow an import per activity file.
 * The price is that a sample is not type-checked against its descriptor; a sample of the wrong
 * shape shows up as an empty or `undefined` part, which a test below rejects.
 */
const samples = new Map<string, readonly unknown[]>([
  ['accountAddActivity', [
    { chain: 'eth', target: { address, kind: 'address' } },
    { chain: 'bch', target: { address: 'bitcoincash:qpmmlusvvrjj9ha2xdgv8xcrpfwsqn5rngt3k26ve2', kind: 'address' } },
    { chain: 'EVM', target: { addresses: [address, '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'], kind: 'addresses' } },
    { chain: 'btc', target: { derivationPath: 'm/0\'/0', kind: 'xpub', xpub: 'xpub6CUGRUonZSQ4TWtTMmzXdrXDtypWKiKrhko4egpiMZbpiaQL2jkwSB1icqYh2cfDfVxdx4df189oLKnC5fSwqPfgyP3hooxujYzAu3fDVmz' } },
  ]],
  ['accountAgnosticRemoveActivity', [{ address, category: 'evm' }]],
  ['accountImportActivity', [{ source: 'csv' }]],
  ['accountRemoveActivity', [
    { chain: 'eth', target: { address, kind: 'address' } },
    { chain: 'btc', target: { kind: 'xpub', xpub: 'xpub6CUGRUonZSQ4TWtTMmzXdrXDtypWKiKrhko4egpiMZbpiaQL2jkwSB1icqYh2cfDfVxdx4df189oLKnC5fSwqPfgyP3hooxujYzAu3fDVmz' } },
  ]],
  ['accountSyncActivity', [{ address, chain: 'eth' }]],
  ['accountingRulesExportActivity', [undefined]],
  ['accountingRulesImportActivity', [undefined]],
  ['accountingRulesResetActivity', [undefined]],
  ['airdropsActivity', [undefined]],
  ['allBalancesActivity', [undefined]],
  ['allBalancesLoginActivity', [undefined]],
  ['assetExportActivity', [undefined]],
  ['assetImportActivity', [undefined]],
  ['assetResetActivity', [undefined]],
  ['assetUpdateActivity', [undefined]],
  ['assetVersionsActivity', [undefined]],
  ['assetMovementMatchActivity', [undefined]],
  ['automaticSyncActivity', [undefined]],
  ['balanceDivergenceActivity', [{ address, asset: 'ETH', evmChain: 'ethereum' }]],
  ['balancesRunActivity', [{ chains: ['btc', 'eth'], mode: 'user' }]],
  ['bankBalancesActivity', [undefined]],
  ['bankEventsActivity', [{ location: 'bank', name: 'Checking' }]],
  ['blockDecodeActivity', [{ blockNumbers: [19000002, 19000001] }]],
  ['bridgeMatchActivity', [undefined]],
  ['chainBalancesActivity', [{ chain: 'eth' }, { chain: 'eth', detect: true }, { chain: 'eth', detect: true, detectAddresses: [address] }]],
  ['chainSyncActivity', [{ chain: 'eth' }]],
  ['conflictResolutionActivity', [undefined]],
  ['csvImportActivity', [{ source: 'cointracking' }]],
  ['dailyPricesActivity', [{ asset: 'ETH', fromTimestamp: 1700000000, interval: 86400, toTimestamp: 1700864000 }]],
  ['decodeActivity', [{ chain: 'eth', ignoreCache: false }, { chain: 'eth', ignoreCache: true }]],
  ['ensResolveActivity', [{ addresses: [address] }]],
  ['erc20InfoActivity', [{ address, evmChain: 'ethereum' }]],
  ['evmAccountDetectionActivity', [undefined]],
  ['exchangeBalancesActivity', [{ location: 'kraken' }]],
  ['exchangeEventsActivity', [{ location: 'kraken', name: 'Main' }]],
  ['exchangeRatesActivity', [{ currency: 'EUR' }, { currency: 'USD' }]],
  ['exchangeSavingsActivity', [{ location: 'binance' }]],
  ['gnosisPayNonceActivity', [undefined]],
  ['gnosisPayVerifyActivity', [undefined]],
  ['historicPriceActivity', [{ fromAsset: 'ETH', timestamp: 1700000000, toAsset: 'USD' }]],
  ['historicPriceBatchActivity', [{ sequence: 1 }]],
  ['historicPriceWaveActivity', [{ sequence: 1 }]],
  ['historicalBalancesActivity', [undefined]],
  ['historyEventsExportActivity', [undefined]],
  ['historySyncActivity', [undefined]],
  ['krakenStakingActivity', [undefined]],
  ['latestPricesActivity', [{ ignoreCache: false, selectedAssets: ['ETH', 'BTC'] }, { ignoreCache: true, selectedAssets: ['ETH', 'BTC'] }]],
  ['latestPricesRefreshActivity', [{ ignoreCache: false, selectedAssets: ['ETH', 'BTC'] }]],
  ['liquidityPoolsActivity', [{ part: 'uniswap-v2' }, { part: 'sushiswap' }]],
  ['liquityActivity', [{ part: 'balances' }, { part: 'pools' }, { part: 'stake' }, { part: 'statistics' }]],
  ['manualBalanceAddActivity', [{ asset: 'ETH', label: 'Cold', location: 'external' }]],
  ['manualBalanceEditActivity', [{ identifier: 7 }]],
  ['manualBalancesFetchActivity', [undefined]],
  ['manualPriceAddActivity', [{ fromAsset: 'ETH', toAsset: 'EUR' }]],
  ['manualSyncActivity', [undefined]],
  ['moduleToggleActivity', [{ enabled: true, module: 'nfts' }, { enabled: false, module: 'nfts' }]],
  ['manualPriceRemoveActivity', [{ fromAsset: 'ETH' }]],
  ['nftAssetsActivity', [{ ignoreCache: false }, { ignoreCache: true }]],
  ['nftBalancesActivity', [undefined]],
  ['onlineEventsActivity', [{ queryType: 'eth_withdrawals' }]],
  ['oracleCacheActivity', [undefined]],
  ['overlaySeriesActivity', [{ asset: 'ETH', locationLabel: address }]],
  ['pnlReportActivity', [undefined]],
  ['pnlReportExportActivity', [undefined]],
  ['pnlReportImportActivity', [undefined]],
  ['protocolCacheActivity', [undefined]],
  ['purgeActivity', [{ purgeable: 'transactions', value: '' }, { purgeable: 'transactions', value: 'eth' }]],
  ['redecodeActivity', [{}, { chains: ['optimism', 'eth'] }]],
  ['repullEthStakingActivity', [{ entryType: 'eth_withdrawal_event', fromTimestamp: 10, toTimestamp: 20, validatorIndices: [1, 2] }]],
  ['repullExchangeEventsActivity', [{ fromTimestamp: 10, location: 'kraken', name: 'Main', toTimestamp: 20 }]],
  ['repullTransactionsActivity', [{ address, chain: 'eth', fromTimestamp: 10, toTimestamp: 20 }]],
  ['sessionCreateActivity', [undefined]],
  ['sessionLoginActivity', [undefined]],
  ['stakingPerformanceActivity', [undefined]],
  ['stakingRowsActivity', [{ part: 'hyperliquid' }, { part: 'solana' }]],
  ['targetedDecodeActivity', [{ chain: 'eth', txRefs: ['0x02', '0x01'] }]],
  ['targetedRedecodeActivity', [{ members: ['eth/0xb', 'block/7'] }]],
  ['tokenDetectionActivity', [{ address, chain: 'eth' }]],
  ['txLookupActivity', [{ requestId: 1, txHash: '0x7a1b' }]],
  ['undecodedBreakdownActivity', [undefined]],
  ['validatorAddActivity', [{ validatorIndex: '12345' }, { publicKey: '0xb0456681b8a0c7c4d4b1b9a48fa6c1bb4bc2a1c5b62f5a0b39c7fa4e53e0c1c1f3d5c6a8b3d2e1f0a9b8c7d6e5f4a3b2' }]],
  ['validatorsActivity', [undefined]],
]);

const sampled = declared.flatMap(({ descriptor, name }) =>
  (samples.get(name) ?? []).map(subject => ({ descriptor, name, subject })),
);

const sampledIds: ActivityId[] = sampled.map(({ descriptor, subject }) => descriptor.id(subject));

describe('activity descriptors', () => {
  it('should find at least one declared descriptor, without which every test below passes vacuously', () => {
    expect(declared.length).toBeGreaterThan(0);
  });

  it('should not export two descriptors under one name, since samples are keyed by it', () => {
    const names = declared.map(({ name }) => name);
    expect(new Set(names).size).toBe(names.length);
  });

  it.each(declared.map(d => [d.name, d] as const))('%s should have a sample subject in this spec', (name) => {
    expect(samples.get(name)?.length, `add a sample subject for ${name}`).toBeGreaterThan(0);
  });

  it('should hold no sample for a descriptor that no longer exists', () => {
    const names = new Set(declared.map(({ name }) => name));
    expect([...samples.keys()].filter(name => !names.has(name))).toStrictEqual([]);
  });

  it.each(sampled.map(s => [s.name, s] as const))('%s should recover its parts from its id, which is what every coarse reader relies on', (_name, { descriptor, subject }) => {
    const id = descriptor.id(subject);

    expect(id.startsWith(`${descriptor.kind}:`) || id === descriptor.kind).toBe(true);
    expect(activityParts(id)).toStrictEqual(descriptor.partsOf(subject).map(String));
  });

  it.each(sampled.map(s => [s.name, s] as const))('%s should build no empty or undefined part, the mark of a sample or key of the wrong shape', (_name, { descriptor, subject }) => {
    for (const part of descriptor.partsOf(subject).map(String)) {
      expect(part).not.toBe('');
      expect(part).not.toBe('undefined');
    }
  });

  it('should give every sampled subject its own id, so no two requests dedup onto one promise', () => {
    expect(new Set(sampledIds).size).toBe(sampledIds.length);
  });

  it.each(declared.map(d => [d.name, d] as const))('%s should keep its batch umbrella apart from every subject id', (_name, { descriptor }) => {
    const batchId = descriptor.batchId([]);

    expect(activityParts(batchId).at(-1)).toBe(ActivityPart.BATCH);
    expect(sampledIds).not.toContain(batchId);
  });
});
