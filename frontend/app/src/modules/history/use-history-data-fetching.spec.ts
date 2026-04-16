import type { LocationLabel } from '@/modules/core/common/location';
import type { TransactionStatus } from '@/modules/history/api/events/use-history-events-api';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryStore } from '@/modules/history/use-history-store';
import '@test/i18n';

const mockFetchAssociatedLocationsApi = vi.fn();
const mockFetchLocationLabelsApi = vi.fn();
const mockGetTransactionStatusSummary = vi.fn();
const mockNotifyError = vi.fn();
const mockLoggerError = vi.fn();
const mockGetErrorMessage = vi.fn((e: unknown): string => (e instanceof Error ? e.message : String(e)));

vi.mock('@/modules/history/api/use-history-api', () => ({
  useHistoryApi: vi.fn((): { fetchAssociatedLocations: typeof mockFetchAssociatedLocationsApi; fetchLocationLabels: typeof mockFetchLocationLabelsApi } => ({
    fetchAssociatedLocations: mockFetchAssociatedLocationsApi,
    fetchLocationLabels: mockFetchLocationLabelsApi,
  })),
}));

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: vi.fn((): { getTransactionStatusSummary: typeof mockGetTransactionStatusSummary } => ({
    getTransactionStatusSummary: mockGetTransactionStatusSummary,
  })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn((): { notifyError: typeof mockNotifyError } => ({
    notifyError: mockNotifyError,
  })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: {
    error: (...args: unknown[]): void => { mockLoggerError(...args); },
  },
}));

vi.mock('@/modules/core/common/logging/error-handling', () => ({
  getErrorMessage: (e: unknown): string => mockGetErrorMessage(e),
}));

const { useHistoryDataFetching } = await import('./use-history-data-fetching');

describe('useHistoryDataFetching', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe('fetchAssociatedLocations', () => {
    it('should call the API and set store state on success', async () => {
      const locations: string[] = ['kraken', 'binance', 'blockchain'];
      mockFetchAssociatedLocationsApi.mockResolvedValue(locations);

      const { fetchAssociatedLocations } = useHistoryDataFetching();
      await fetchAssociatedLocations();

      expect(mockFetchAssociatedLocationsApi).toHaveBeenCalledOnce();

      const store = useHistoryStore();
      const { associatedLocations } = storeToRefs(store);
      expect(get(associatedLocations)).toEqual(locations);
    });

    it('should log error and show notification on failure', async () => {
      const error = new Error('Network failure');
      mockFetchAssociatedLocationsApi.mockRejectedValue(error);

      const { fetchAssociatedLocations } = useHistoryDataFetching();
      await fetchAssociatedLocations();

      expect(mockLoggerError).toHaveBeenCalledWith(error);
      expect(mockGetErrorMessage).toHaveBeenCalledWith(error);
      expect(mockNotifyError).toHaveBeenCalledOnce();
      expect(mockNotifyError).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
      );
    });
  });

  describe('fetchLocationLabels', () => {
    it('should call the API and set store state on success', async () => {
      const labels: LocationLabel[] = [
        { location: 'kraken', locationLabel: 'My Exchange' },
        { location: 'binance', locationLabel: 'Cold Wallet' },
      ];
      mockFetchLocationLabelsApi.mockResolvedValue(labels);

      const { fetchLocationLabels } = useHistoryDataFetching();
      await fetchLocationLabels();

      expect(mockFetchLocationLabelsApi).toHaveBeenCalledOnce();

      const store = useHistoryStore();
      const { locationLabels } = storeToRefs(store);
      expect(get(locationLabels)).toEqual(labels);
    });

    it('should log error and show notification on failure', async () => {
      const error = new Error('API error');
      mockFetchLocationLabelsApi.mockRejectedValue(error);

      const { fetchLocationLabels } = useHistoryDataFetching();
      await fetchLocationLabels();

      expect(mockLoggerError).toHaveBeenCalledWith(error);
      expect(mockGetErrorMessage).toHaveBeenCalledWith(error);
      expect(mockNotifyError).toHaveBeenCalledOnce();
      expect(mockNotifyError).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
      );
    });
  });

  describe('fetchTransactionStatusSummary', () => {
    it('should call the API and set store state on success', async () => {
      const status: TransactionStatus = {
        evmLastQueriedTs: 1000,
        exchangesLastQueriedTs: 2000,
        hasEvmAccounts: true,
        hasExchangesAccounts: false,
        undecodedTxCount: 5,
      };
      mockGetTransactionStatusSummary.mockResolvedValue(status);

      const { fetchTransactionStatusSummary } = useHistoryDataFetching();
      await fetchTransactionStatusSummary();

      expect(mockGetTransactionStatusSummary).toHaveBeenCalledOnce();

      const store = useHistoryStore();
      const { transactionStatusSummary } = storeToRefs(store);
      expect(get(transactionStatusSummary)).toEqual(status);
    });

    it('should log error but not show notification on failure', async () => {
      const error = new Error('Status fetch failed');
      mockGetTransactionStatusSummary.mockRejectedValue(error);

      const { fetchTransactionStatusSummary } = useHistoryDataFetching();
      await fetchTransactionStatusSummary();

      expect(mockLoggerError).toHaveBeenCalledWith(error);
      expect(mockNotifyError).not.toHaveBeenCalled();
    });
  });
});
