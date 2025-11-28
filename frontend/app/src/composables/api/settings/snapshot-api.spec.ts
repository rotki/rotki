import type { SnapshotPayload } from '@/types/snapshots';
import { BigNumber } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BalanceType } from '@/types/balances';
import { useSnapshotApi } from './snapshot-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/settings/snapshot-api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getSnapshotData', () => {
    it('fetches snapshot data for a given timestamp', async () => {
      const mockSnapshot = {
        balances_snapshot: [
          {
            amount: '1.5',
            asset_identifier: 'ETH',
            category: 'asset',
            timestamp: 1700000000,
            usd_value: '3000.00',
          },
        ],
        location_data_snapshot: [
          {
            location: 'binance',
            timestamp: 1700000000,
            usd_value: '5000.00',
          },
        ],
      };

      server.use(
        http.get(`${backendUrl}/api/1/snapshots/:timestamp`, () =>
          HttpResponse.json({
            result: mockSnapshot,
            message: '',
          })),
      );

      const { getSnapshotData } = useSnapshotApi();
      const result = await getSnapshotData(1700000000);

      expect(result.balancesSnapshot).toHaveLength(1);
      expect(result.balancesSnapshot[0].assetIdentifier).toBe('ETH');
      expect(result.balancesSnapshot[0].amount).toBeInstanceOf(BigNumber);
      expect(result.balancesSnapshot[0].amount.toString()).toBe('1.5');
      expect(result.locationDataSnapshot).toHaveLength(1);
      expect(result.locationDataSnapshot[0].location).toBe('binance');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/snapshots/:timestamp`, () =>
          HttpResponse.json({
            result: null,
            message: 'Snapshot not found',
          })),
      );

      const { getSnapshotData } = useSnapshotApi();

      await expect(getSnapshotData(1700000000))
        .rejects
        .toThrow('Snapshot not found');
    });
  });

  describe('updateSnapshotData', () => {
    it('sends PATCH request with snake_case payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      server.use(
        http.patch(`${backendUrl}/api/1/snapshots/:timestamp`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { updateSnapshotData } = useSnapshotApi();
      const payload: SnapshotPayload = {
        balancesSnapshot: [
          {
            timestamp: 1700000000,
            category: BalanceType.ASSET,
            assetIdentifier: 'BTC',
            amount: '2.0',
            usdValue: '80000.00',
          },
        ],
        locationDataSnapshot: [
          {
            timestamp: 1700000000,
            location: 'kraken',
            usdValue: '10000.00',
          },
        ],
      };

      const result = await updateSnapshotData(1700000000, payload);

      expect(result).toBe(true);
      expect(capturedUrl).toContain('/snapshots/1700000000');
      expect(capturedBody).toEqual({
        balances_snapshot: [
          {
            timestamp: 1700000000,
            category: 'asset',
            asset_identifier: 'BTC',
            amount: '2.0',
            usd_value: '80000.00',
          },
        ],
        location_data_snapshot: [
          {
            timestamp: 1700000000,
            location: 'kraken',
            usd_value: '10000.00',
          },
        ],
      });
    });
  });

  describe('exportSnapshotCSV', () => {
    it('sends GET request with action and path params in snake_case', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/snapshots/:timestamp`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { exportSnapshotCSV } = useSnapshotApi();
      const result = await exportSnapshotCSV({
        path: '/home/user/exports',
        timestamp: 1700000000,
      });

      expect(result).toBe(true);
      expect(capturedParams!.get('action')).toBe('export');
      expect(capturedParams!.get('path')).toBe('/home/user/exports');
    });
  });

  describe('downloadSnapshot', () => {
    it('sends GET request with download action param', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/snapshots/:timestamp`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return new HttpResponse(new Blob(['test data']), {
            headers: { 'Content-Type': 'application/octet-stream' },
          });
        }),
      );

      const { downloadSnapshot } = useSnapshotApi();
      await downloadSnapshot(1700000000);

      expect(capturedParams!.get('action')).toBe('download');
    });
  });

  describe('deleteSnapshot', () => {
    it('sends DELETE request with snake_case payload in body', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/snapshots`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteSnapshot } = useSnapshotApi();
      const result = await deleteSnapshot({ timestamp: 1700000000 });

      expect(result).toBe(true);
      expect(capturedBody).toEqual({
        timestamp: 1700000000,
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/snapshots`, () =>
          HttpResponse.json({
            result: null,
            message: 'Cannot delete snapshot',
          })),
      );

      const { deleteSnapshot } = useSnapshotApi();

      await expect(deleteSnapshot({ timestamp: 1700000000 }))
        .rejects
        .toThrow('Cannot delete snapshot');
    });
  });

  describe('importBalancesSnapshot', () => {
    it('sends PUT request with snake_case file paths', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/snapshots`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { importBalancesSnapshot } = useSnapshotApi();
      const result = await importBalancesSnapshot(
        '/path/to/balances.csv',
        '/path/to/location_data.csv',
      );

      expect(result).toBe(true);
      expect(capturedBody).toEqual({
        balances_snapshot_file: '/path/to/balances.csv',
        location_data_snapshot_file: '/path/to/location_data.csv',
      });
    });

    it('throws error on import failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/snapshots`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid file format',
          })),
      );

      const { importBalancesSnapshot } = useSnapshotApi();

      await expect(importBalancesSnapshot('/invalid.csv', '/invalid2.csv'))
        .rejects
        .toThrow('Invalid file format');
    });
  });

  describe('uploadBalancesSnapshot', () => {
    it('sends POST request with multipart form data', async () => {
      let capturedFormData: FormData | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/snapshots`, async ({ request }) => {
          capturedFormData = await request.formData() as unknown as FormData;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { uploadBalancesSnapshot } = useSnapshotApi();
      const balancesFile = new File(['balances content'], 'balances.csv', { type: 'text/csv' });
      const locationFile = new File(['location content'], 'location.csv', { type: 'text/csv' });

      const result = await uploadBalancesSnapshot(balancesFile, locationFile);

      expect(result).toBe(true);
      expect(capturedFormData).not.toBeNull();
      expect(capturedFormData!.get('balances_snapshot_file')).toBeTruthy();
      expect(capturedFormData!.get('location_data_snapshot_file')).toBeTruthy();
    });

    it('throws error on upload failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/snapshots`, () =>
          HttpResponse.json({
            result: null,
            message: 'Upload failed',
          })),
      );

      const { uploadBalancesSnapshot } = useSnapshotApi();
      const balancesFile = new File(['content'], 'balances.csv');
      const locationFile = new File(['content'], 'location.csv');

      await expect(uploadBalancesSnapshot(balancesFile, locationFile))
        .rejects
        .toThrow('Upload failed');
    });
  });
});
