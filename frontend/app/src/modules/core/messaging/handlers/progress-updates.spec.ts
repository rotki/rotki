import type { ProgressUpdateResultData } from '../types/status-types';
import { Blockchain } from '@rotki/common';
import { mockT } from '@test/i18n';
import { createMock } from '@test/utils/create-mock';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createProgressUpdateHandler } from '@/modules/core/messaging/handlers/progress-updates';
import { SocketMessageProgressUpdateSubType } from '@/modules/core/messaging/types/base';
import { decodeActivity, decodeActivityId } from '@/modules/history/events/tx/decode-activity';
import { protocolCacheActivity } from '@/modules/history/protocol-cache-activity';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { readActivityDetail, useActivityDetail } from '@/modules/task-center/use-activity-detail';

const mockSetUndecodedTransactionsStatus = vi.fn();
const mockSetHistoricalDailyPriceStatus = vi.fn();
const mockSetHistoricalPriceStatus = vi.fn();
const mockSetStatsPriceQueryStatus = vi.fn();
const mockReportProgress = vi.fn();
const mockReportProgressByPrefix = vi.fn();
/** Which activity ids count as running, so a test can put one parent or the other in flight. */
let runningIds: string[] = [];
const mockStatusOf = vi.fn((kind: ActivityKind, ...parts: (string | number)[]) => ({
  active: runningIds.includes(makeActivityId(kind, ...parts)),
  everCompleted: false,
  running: runningIds.includes(makeActivityId(kind, ...parts)),
}));

type SupportedChains = typeof import('@/modules/core/common/use-supported-chains');

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn<SupportedChains['useSupportedChains']>(() =>
    createMock<ReturnType<SupportedChains['useSupportedChains']>>({
      // The decoder's spelling, so a route that forgets to canonicalise composes the wrong id.
      matchChain: (chain: string) => (chain === 'ethereum' ? Blockchain.ETH : undefined),
    })),
} satisfies Partial<SupportedChains>));

vi.mock('@/modules/history/use-decoding-status-store', () => ({
  useDecodingStatusStore: vi.fn(() => ({
    setUndecodedTransactionsStatus: mockSetUndecodedTransactionsStatus,
  })),
}));

vi.mock('@/modules/assets/prices/use-historic-cache-price-store', () => ({
  useHistoricCachePriceStore: vi.fn(() => ({
    setHistoricalDailyPriceStatus: mockSetHistoricalDailyPriceStatus,
    setHistoricalPriceStatus: mockSetHistoricalPriceStatus,
    setStatsPriceQueryStatus: mockSetStatsPriceQueryStatus,
  })),
}));

vi.mock('@/modules/task-center/use-task-orchestrator', () => ({
  useTaskOrchestrator: vi.fn(() => ({
    reportProgress: mockReportProgress,
    reportProgressByPrefix: mockReportProgressByPrefix,
    statusOf: mockStatusOf,
  })),
}));

function data(subtype: SocketMessageProgressUpdateSubType): ProgressUpdateResultData {
  return createMock<ProgressUpdateResultData>({ subtype });
}

describe('createProgressUpdateHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useActivityDetail().resetDetails();
    vi.clearAllMocks();
    runningIds = [];
  });

  it('should route undecoded transaction updates', async () => {
    const handler = createProgressUpdateHandler(mockT);
    const result = await handler.handle(data(SocketMessageProgressUpdateSubType.UNDECODED_TRANSACTIONS));

    expect(mockSetUndecodedTransactionsStatus).toHaveBeenCalledOnce();
    expect(result).toBeNull();
  });

  it('should report decode progress onto the chain activity under its canonical chain id', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(createMock<ProgressUpdateResultData>({
      chain: 'ethereum',
      processed: 3,
      subtype: SocketMessageProgressUpdateSubType.UNDECODED_TRANSACTIONS,
      total: 10,
    }));

    // Both variants of the chain-wide decode, never a targeted one.
    expect(mockReportProgress).toHaveBeenCalledWith(decodeActivityId('eth', false), { current: 3, total: 10 });
    expect(mockReportProgress).toHaveBeenCalledWith(decodeActivityId('eth', true), { current: 3, total: 10 });
    expect(mockReportProgress).not.toHaveBeenCalledWith(
      expect.stringContaining('ethereum'),
      expect.anything(),
    );
  });

  it('should fall back to the lowercased chain when it matches no known chain', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(createMock<ProgressUpdateResultData>({
      chain: 'Hyperliquid',
      processed: 1,
      subtype: SocketMessageProgressUpdateSubType.UNDECODED_TRANSACTIONS,
      total: 2,
    }));

    expect(mockReportProgress).toHaveBeenCalledWith(
      decodeActivityId('hyperliquid', false),
      { current: 1, total: 2 },
    );
  });

  describe('protocol cache rows', () => {
    const curveOnEthereum = { chain: 'ethereum', processed: 2, protocol: 'curve', total: 8 };
    const aaveOnEthereum = { chain: 'ethereum', processed: 1, protocol: 'aave', total: 4 };
    const aaveOnOptimism = { chain: 'optimism', processed: 1, protocol: 'aave', total: 4 };

    async function handleProtocolCacheFrame(frame: typeof curveOnEthereum): Promise<void> {
      await createProgressUpdateHandler(mockT).handle(createMock<ProgressUpdateResultData>({
        ...frame,
        subtype: SocketMessageProgressUpdateSubType.PROTOCOL_CACHE_UPDATES,
      }));
    }

    it('should accumulate every pair a running cache refresh has reached, the newest first', async () => {
      runningIds = [protocolCacheActivity.id()];

      await handleProtocolCacheFrame(curveOnEthereum);
      await handleProtocolCacheFrame(aaveOnOptimism);

      expect(get(readActivityDetail(protocolCacheActivity, undefined))?.protocols)
        .toStrictEqual([aaveOnOptimism, { ...curveOnEthereum, processed: 8 }]);
    });

    it('should attach only the decoding chain\'s frames to its decode, under the canonical chain id', async () => {
      const subject = { chain: 'eth', ignoreCache: false };
      runningIds = [decodeActivity.id(subject)];

      // The frames say 'ethereum' while the activity is keyed by 'eth'.
      await handleProtocolCacheFrame(curveOnEthereum);
      await handleProtocolCacheFrame(aaveOnOptimism);
      await handleProtocolCacheFrame(aaveOnEthereum);

      expect(get(readActivityDetail(decodeActivity, subject))?.protocols)
        .toStrictEqual([aaveOnEthereum, { ...curveOnEthereum, processed: 8 }]);
    });

    it('should publish nothing when neither parent is running', async () => {
      await handleProtocolCacheFrame(curveOnEthereum);

      expect(get(readActivityDetail(protocolCacheActivity, undefined))).toBeUndefined();
      expect(get(readActivityDetail(decodeActivity, { chain: 'eth', ignoreCache: false }))).toBeUndefined();
    });

    it('should keep a stopped refresh\'s rows as they were when it stopped', async () => {
      runningIds = [protocolCacheActivity.id()];
      await handleProtocolCacheFrame(curveOnEthereum);

      runningIds = [];
      await handleProtocolCacheFrame(aaveOnEthereum);

      expect(get(readActivityDetail(protocolCacheActivity, undefined))?.protocols).toStrictEqual([curveOnEthereum]);
    });

    it('should publish against the forced decode when that is the live variant', async () => {
      const forced = { chain: 'eth', ignoreCache: true };
      runningIds = [decodeActivity.id(forced)];

      await handleProtocolCacheFrame(curveOnEthereum);

      expect(get(readActivityDetail(decodeActivity, forced))?.protocols).toStrictEqual([curveOnEthereum]);
      expect(get(readActivityDetail(decodeActivity, { chain: 'eth', ignoreCache: false }))).toBeUndefined();
    });
  });

  it('should route historical price query updates', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(data(SocketMessageProgressUpdateSubType.HISTORICAL_PRICE_QUERY_STATUS));

    expect(mockSetHistoricalDailyPriceStatus).toHaveBeenCalledOnce();
  });

  it('should report liquity staking query progress onto its activity', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(createMock<ProgressUpdateResultData>({
      processed: 1,
      subtype: SocketMessageProgressUpdateSubType.LIQUITY_STAKING_QUERY,
      total: 2,
    }));

    expect(mockReportProgress).toHaveBeenCalledWith(
      makeActivityId(ActivityKind.LIQUITY, ActivityPart.STAKE),
      { current: 1, total: 2 },
    );
  });

  it('should route stats price query updates', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(data(SocketMessageProgressUpdateSubType.STATS_PRICE_QUERY));

    expect(mockSetStatsPriceQueryStatus).toHaveBeenCalledOnce();
  });

  it('should report a stats price backfill onto the query it is a phase of', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(createMock<ProgressUpdateResultData>({
      counterparty: 'liquity',
      processed: 4,
      subtype: SocketMessageProgressUpdateSubType.STATS_PRICE_QUERY,
      total: 8,
    }));

    expect(mockReportProgress).toHaveBeenCalledWith(
      makeActivityId(ActivityKind.LIQUITY, ActivityPart.STATISTICS),
      { current: 4, total: 8 },
    );
  });

  it('should report nothing for a counterparty with no activity of its own', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(createMock<ProgressUpdateResultData>({
      counterparty: 'something-new',
      processed: 4,
      subtype: SocketMessageProgressUpdateSubType.STATS_PRICE_QUERY,
      total: 8,
    }));

    expect(mockSetStatsPriceQueryStatus).toHaveBeenCalledOnce();
    expect(mockReportProgress).not.toHaveBeenCalled();
  });

  it('should route multiple prices query updates', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(data(SocketMessageProgressUpdateSubType.MULTIPLE_PRICES_QUERY_STATUS));

    expect(mockSetHistoricalPriceStatus).toHaveBeenCalledOnce();
  });

  it('should report multiple prices progress onto the batch activities only', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(createMock<ProgressUpdateResultData>({
      processed: 4,
      subtype: SocketMessageProgressUpdateSubType.MULTIPLE_PRICES_QUERY_STATUS,
      total: 9,
    }));

    // BATCH is part of the prefix, so single-pair price activities are left alone.
    expect(mockReportProgressByPrefix).toHaveBeenCalledWith(
      { current: 4, total: 9 },
      ActivityKind.PRICES,
      ActivityPart.HISTORIC,
      ActivityPart.BATCH,
    );
  });

  it('should route historical balance processing updates', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(data(SocketMessageProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING));

    expect(mockReportProgress).toHaveBeenCalledOnce();
    expect(mockReportProgress).toHaveBeenCalledWith(
      makeActivityId(ActivityKind.HISTORICAL_BALANCES),
      expect.objectContaining({ current: expect.anything(), total: expect.anything() }),
    );
  });

  it('should delegate csv import results to the csv handler', async () => {
    const handler = createProgressUpdateHandler(mockT);
    const result = await handler.handle(createMock<ProgressUpdateResultData>({
      messages: [],
      processed: 1,
      sourceName: 'binance',
      subtype: SocketMessageProgressUpdateSubType.CSV_IMPORT_RESULT,
      total: 1,
    }));

    expect(result).not.toBeNull();
  });

  it('should not touch any store for an unknown subtype', async () => {
    const handler = createProgressUpdateHandler(mockT);
    const result = await handler.handle(createMock<ProgressUpdateResultData>({}));

    expect(result).toBeNull();
    expect(mockSetUndecodedTransactionsStatus).not.toHaveBeenCalled();
    expect(mockReportProgress).not.toHaveBeenCalled();
  });
});
