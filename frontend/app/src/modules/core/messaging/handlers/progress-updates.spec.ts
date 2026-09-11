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
const mockSetProtocolCacheStatus = vi.fn();
const mockSetReceivingProtocolCacheStatus = vi.fn();
const mockSetHistoricalDailyPriceStatus = vi.fn();
const mockSetHistoricalPriceStatus = vi.fn();
const mockSetStatsPriceQueryStatus = vi.fn();
const mockReportProgress = vi.fn();
const mockReportProgressByPrefix = vi.fn();
/** What the protocol-cache store has accumulated, as the handler reads it back. */
let protocolCacheRows: { chain: string; protocol: string; processed: number; total: number }[] = [];
/** Which activity ids count as running, so a test can put one parent or the other in flight. */
let runningIds: string[] = [];
const mockStatusOf = vi.fn((kind: ActivityKind, ...parts: (string | number)[]) => ({
  active: runningIds.includes(makeActivityId(kind, ...parts)),
  everCompleted: false,
  running: runningIds.includes(makeActivityId(kind, ...parts)),
}));
const mockNotifyHistoricalBalanceProcessingCompleted = vi.fn();

type SupportedChains = typeof import('@/modules/core/common/use-supported-chains');

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn<SupportedChains['useSupportedChains']>(() =>
    createMock<ReturnType<SupportedChains['useSupportedChains']>>({
      // The decoder's spelling, so a route that forgets to canonicalise composes the wrong id.
      matchChain: (chain: string) => (chain === 'ethereum' ? Blockchain.ETH : undefined),
    })),
} satisfies Partial<SupportedChains>));

vi.mock('@/modules/history/data-issues/use-data-issues-inbox-store', () => ({
  useDataIssuesInboxStore: vi.fn(() => ({
    notifyHistoricalBalanceProcessingCompleted: mockNotifyHistoricalBalanceProcessingCompleted,
  })),
}));

vi.mock('@/modules/history/use-decoding-status-store', () => ({
  useDecodingStatusStore: vi.fn(() => ({
    setUndecodedTransactionsStatus: mockSetUndecodedTransactionsStatus,
  })),
}));

vi.mock('@/modules/history/use-protocol-cache-status-store', () => ({
  useProtocolCacheStatusStore: vi.fn(() => ({
    get protocolCacheStatus(): typeof protocolCacheRows {
      return protocolCacheRows;
    },
    setProtocolCacheStatus: mockSetProtocolCacheStatus,
    setReceivingProtocolCacheStatus: mockSetReceivingProtocolCacheStatus,
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
    protocolCacheRows = [];
    runningIds = [];
  });

  it('should route undecoded transaction updates and stop the receiving flag', async () => {
    const handler = createProgressUpdateHandler(mockT);
    const result = await handler.handle(data(SocketMessageProgressUpdateSubType.UNDECODED_TRANSACTIONS));

    expect(mockSetReceivingProtocolCacheStatus).toHaveBeenCalledWith(false);
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

  it('should route protocol cache updates', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(data(SocketMessageProgressUpdateSubType.PROTOCOL_CACHE_UPDATES));

    expect(mockSetProtocolCacheStatus).toHaveBeenCalledOnce();
  });

  describe('protocol cache rows', () => {
    const curveOnEthereum = { chain: 'ethereum', processed: 2, protocol: 'curve', total: 8 };
    const aaveOnOptimism = { chain: 'optimism', processed: 1, protocol: 'aave', total: 4 };

    async function handleProtocolCacheFrame(chain = 'ethereum'): Promise<void> {
      await createProgressUpdateHandler(mockT).handle(createMock<ProgressUpdateResultData>({
        chain,
        subtype: SocketMessageProgressUpdateSubType.PROTOCOL_CACHE_UPDATES,
      }));
    }

    it('should attach every accumulated row to a running cache refresh', async () => {
      protocolCacheRows = [curveOnEthereum, aaveOnOptimism];
      runningIds = [protocolCacheActivity.id()];

      await handleProtocolCacheFrame();

      expect(get(readActivityDetail(protocolCacheActivity, undefined))?.protocols)
        .toStrictEqual([curveOnEthereum, aaveOnOptimism]);
    });

    it('should attach only the decoding chain\'s rows to its decode, under the canonical chain id', async () => {
      protocolCacheRows = [curveOnEthereum, aaveOnOptimism];
      const subject = { chain: 'eth', ignoreCache: false };
      runningIds = [decodeActivity.id(subject)];

      // The frame says 'ethereum' while the activity is keyed by 'eth'.
      await handleProtocolCacheFrame();

      expect(get(readActivityDetail(decodeActivity, subject))?.protocols).toStrictEqual([curveOnEthereum]);
    });

    it('should publish nothing when neither parent is running', async () => {
      protocolCacheRows = [curveOnEthereum];

      await handleProtocolCacheFrame();

      expect(get(readActivityDetail(protocolCacheActivity, undefined))).toBeUndefined();
      expect(get(readActivityDetail(decodeActivity, { chain: 'eth', ignoreCache: false }))).toBeUndefined();
    });

    it('should publish against the forced decode when that is the live variant', async () => {
      protocolCacheRows = [curveOnEthereum];
      const forced = { chain: 'eth', ignoreCache: true };
      runningIds = [decodeActivity.id(forced)];

      await handleProtocolCacheFrame();

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

  it('should signal data-issue refresh when historical balance processing completes', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(createMock<ProgressUpdateResultData>({
      processed: 2,
      subtype: SocketMessageProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING,
      total: 2,
    }));

    expect(mockNotifyHistoricalBalanceProcessingCompleted).toHaveBeenCalledOnce();
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
    expect(mockSetProtocolCacheStatus).not.toHaveBeenCalled();
    expect(mockReportProgress).not.toHaveBeenCalled();
  });
});
