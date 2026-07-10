import type { ProgressUpdateResultData } from '../types/status-types';
import { mockT } from '@test/i18n';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createProgressUpdateHandler } from '@/modules/core/messaging/handlers/progress-updates';
import { SocketMessageProgressUpdateSubType } from '@/modules/core/messaging/types/base';

const mockSetUndecodedTransactionsStatus = vi.fn();
const mockSetProtocolCacheStatus = vi.fn();
const mockSetReceivingProtocolCacheStatus = vi.fn();
const mockSetHistoricalDailyPriceStatus = vi.fn();
const mockSetHistoricalPriceStatus = vi.fn();
const mockSetStatsPriceQueryStatus = vi.fn();
const mockSetStakingQueryStatus = vi.fn();
const mockSetProcessingProgress = vi.fn();

vi.mock('@/modules/history/use-decoding-status-store', () => ({
  useDecodingStatusStore: vi.fn(() => ({
    setUndecodedTransactionsStatus: mockSetUndecodedTransactionsStatus,
  })),
}));

vi.mock('@/modules/history/use-protocol-cache-status-store', () => ({
  useProtocolCacheStatusStore: vi.fn(() => ({
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

vi.mock('@/modules/staking/liquity/use-liquity-store', () => ({
  useLiquityStore: vi.fn(() => ({
    setStakingQueryStatus: mockSetStakingQueryStatus,
  })),
}));

vi.mock('@/modules/history/balances/use-historical-balances-store', () => ({
  useHistoricalBalancesStore: vi.fn(() => ({
    setProcessingProgress: mockSetProcessingProgress,
  })),
}));

function data(subtype: SocketMessageProgressUpdateSubType): ProgressUpdateResultData {
  return createMock<ProgressUpdateResultData>({ subtype });
}

describe('createProgressUpdateHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should route undecoded transaction updates and stop the receiving flag', async () => {
    const handler = createProgressUpdateHandler(mockT);
    const result = await handler.handle(data(SocketMessageProgressUpdateSubType.UNDECODED_TRANSACTIONS));

    expect(mockSetReceivingProtocolCacheStatus).toHaveBeenCalledWith(false);
    expect(mockSetUndecodedTransactionsStatus).toHaveBeenCalledOnce();
    expect(result).toBeNull();
  });

  it('should route protocol cache updates', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(data(SocketMessageProgressUpdateSubType.PROTOCOL_CACHE_UPDATES));

    expect(mockSetProtocolCacheStatus).toHaveBeenCalledOnce();
  });

  it('should route historical price query updates', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(data(SocketMessageProgressUpdateSubType.HISTORICAL_PRICE_QUERY_STATUS));

    expect(mockSetHistoricalDailyPriceStatus).toHaveBeenCalledOnce();
  });

  it('should route liquity staking query updates', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(data(SocketMessageProgressUpdateSubType.LIQUITY_STAKING_QUERY));

    expect(mockSetStakingQueryStatus).toHaveBeenCalledOnce();
  });

  it('should route stats price query updates', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(data(SocketMessageProgressUpdateSubType.STATS_PRICE_QUERY));

    expect(mockSetStatsPriceQueryStatus).toHaveBeenCalledOnce();
  });

  it('should route multiple prices query updates', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(data(SocketMessageProgressUpdateSubType.MULTIPLE_PRICES_QUERY_STATUS));

    expect(mockSetHistoricalPriceStatus).toHaveBeenCalledOnce();
  });

  it('should route historical balance processing updates', async () => {
    const handler = createProgressUpdateHandler(mockT);
    await handler.handle(data(SocketMessageProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING));

    expect(mockSetProcessingProgress).toHaveBeenCalledOnce();
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
    expect(mockSetProcessingProgress).not.toHaveBeenCalled();
  });
});
