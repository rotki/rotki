import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryApi } from './index';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/history/index', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getProgress', () => {
    it('fetches report progress', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/status`, () =>
          HttpResponse.json({
            result: {
              processing_state: 'idle',
              total_progress: '100%',
            },
            message: '',
          })),
      );

      const { getProgress } = useHistoryApi();
      const result = await getProgress();

      expect(result.processingState).toBe('idle');
      expect(result.totalProgress).toBe('100%');
    });

    it('handles in-progress state', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/status`, () =>
          HttpResponse.json({
            result: {
              processing_state: 'processing',
              total_progress: '45%',
            },
            message: '',
          })),
      );

      const { getProgress } = useHistoryApi();
      const result = await getProgress();

      expect(result.processingState).toBe('processing');
      expect(result.totalProgress).toBe('45%');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/status`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to get progress',
          })),
      );

      const { getProgress } = useHistoryApi();

      await expect(getProgress())
        .rejects
        .toThrow('Failed to get progress');
    });
  });

  describe('fetchAssociatedLocations', () => {
    it('fetches associated locations', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/locations/associated`, () =>
          HttpResponse.json({
            result: ['binance', 'kraken', 'blockchain'],
            message: '',
          })),
      );

      const { fetchAssociatedLocations } = useHistoryApi();
      const result = await fetchAssociatedLocations();

      expect(result).toEqual(['binance', 'kraken', 'blockchain']);
    });

    it('returns empty array when no locations', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/locations/associated`, () =>
          HttpResponse.json({
            result: [],
            message: '',
          })),
      );

      const { fetchAssociatedLocations } = useHistoryApi();
      const result = await fetchAssociatedLocations();

      expect(result).toEqual([]);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/locations/associated`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch associated locations',
          })),
      );

      const { fetchAssociatedLocations } = useHistoryApi();

      await expect(fetchAssociatedLocations())
        .rejects
        .toThrow('Failed to fetch associated locations');
    });
  });

  describe('fetchAllLocations', () => {
    it('fetches all locations with exchange details', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/locations/all`, () =>
          HttpResponse.json({
            result: {
              locations: {
                binance: {
                  label: 'Binance',
                  icon: 'binance.svg',
                  isExchange: true,
                  exchangeDetails: {
                    isExchangeWithKey: true,
                    isExchangeWithPassphrase: false,
                    isExchangeWithoutApiSecret: false,
                  },
                },
                blockchain: {
                  label: 'Blockchain',
                  icon: 'blockchain.svg',
                  isExchange: false,
                },
              },
            },
            message: '',
          })),
      );

      const { fetchAllLocations } = useHistoryApi();
      const result = await fetchAllLocations();

      expect(result.locations.binance.label).toBe('Binance');
      expect(result.locations.binance.isExchange).toBe(true);
      expect(result.locations.binance.exchangeDetails?.isExchangeWithKey).toBe(true);
      expect(result.locations.blockchain.isExchange).toBe(false);
    });

    it('handles empty locations', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/locations/all`, () =>
          HttpResponse.json({
            result: {
              locations: {},
            },
            message: '',
          })),
      );

      const { fetchAllLocations } = useHistoryApi();
      const result = await fetchAllLocations();

      expect(result.locations).toEqual({});
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/locations/all`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch all locations',
          })),
      );

      const { fetchAllLocations } = useHistoryApi();

      await expect(fetchAllLocations())
        .rejects
        .toThrow('Failed to fetch all locations');
    });
  });

  describe('fetchLocationLabels', () => {
    it('fetches location labels and filters empty labels', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/locations/labels`, () =>
          HttpResponse.json({
            result: [
              { location: 'binance', location_label: 'My Binance' },
              { location: 'kraken', location_label: 'Main Kraken' },
              { location: 'empty', location_label: '' },
            ],
            message: '',
          })),
      );

      const { fetchLocationLabels } = useHistoryApi();
      const result = await fetchLocationLabels();

      // Empty labels should be filtered out
      expect(result).toHaveLength(2);
      expect(result[0].location).toBe('binance');
      expect(result[0].locationLabel).toBe('My Binance');
      expect(result[1].location).toBe('kraken');
      expect(result[1].locationLabel).toBe('Main Kraken');
    });

    it('returns empty array when no labels', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/locations/labels`, () =>
          HttpResponse.json({
            result: [],
            message: '',
          })),
      );

      const { fetchLocationLabels } = useHistoryApi();
      const result = await fetchLocationLabels();

      expect(result).toEqual([]);
    });

    it('filters out all items with empty locationLabel', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/locations/labels`, () =>
          HttpResponse.json({
            result: [
              { location: 'loc1', location_label: '' },
              { location: 'loc2', location_label: '' },
            ],
            message: '',
          })),
      );

      const { fetchLocationLabels } = useHistoryApi();
      const result = await fetchLocationLabels();

      expect(result).toEqual([]);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/locations/labels`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch location labels',
          })),
      );

      const { fetchLocationLabels } = useHistoryApi();

      await expect(fetchLocationLabels())
        .rejects
        .toThrow('Failed to fetch location labels');
    });
  });
});
