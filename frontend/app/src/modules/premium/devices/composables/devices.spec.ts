import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HTTPStatus } from '@/types/api/http';
import { usePremiumDevicesApi } from './devices';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('modules/premium/devices/composables/devices', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('usePremiumDevicesApi', () => {
    describe('fetchPremiumDevices', () => {
      it('sends GET request and returns parsed response', async () => {
        server.use(
          http.get(`${backendUrl}/api/1/premium/devices`, () =>
            HttpResponse.json({
              result: {
                current_device_id: 'device-1',
                limit: 5,
                devices: [
                  {
                    device_identifier: 'device-1',
                    device_name: 'My Linux Computer',
                    last_seen_at: 1700000000,
                    platform: 'linux',
                    user: 'testuser',
                  },
                  {
                    device_identifier: 'device-2',
                    device_name: 'My Mac',
                    last_seen_at: 1700000100,
                    platform: 'darwin',
                    user: 'testuser',
                  },
                  {
                    device_identifier: 'device-3',
                    device_name: 'My Windows PC',
                    last_seen_at: 1700000200,
                    platform: 'windows',
                    user: 'testuser',
                  },
                  {
                    device_identifier: 'device-4',
                    device_name: 'Docker Instance',
                    last_seen_at: 1700000300,
                    platform: 'docker',
                    user: 'testuser',
                  },
                  {
                    device_identifier: 'device-5',
                    device_name: 'K8s Pod',
                    last_seen_at: 1700000400,
                    platform: 'kubernetes',
                    user: 'testuser',
                  },
                ],
              },
              message: '',
            })),
        );

        const { fetchPremiumDevices } = usePremiumDevicesApi();
        const result = await fetchPremiumDevices();

        expect(result.currentDeviceId).toBe('device-1');
        expect(result.limit).toBe(5);
        expect(result.devices).toHaveLength(5);
        expect(result.devices[0].deviceName).toBe('My Linux Computer');
        expect(result.devices[0].platform).toBe('linux');
        expect(result.devices[1].platform).toBe('darwin');
        expect(result.devices[2].platform).toBe('windows');
        expect(result.devices[3].platform).toBe('docker');
        expect(result.devices[4].platform).toBe('kubernetes');
      });
    });

    describe('updatePremiumDevice', () => {
      it('sends PATCH request with snake_case payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.patch(`${backendUrl}/api/1/premium/devices`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { updatePremiumDevice } = usePremiumDevicesApi();
        const result = await updatePremiumDevice({
          deviceIdentifier: 'device-1',
          deviceName: 'Updated Name',
        });

        expect(capturedBody).toEqual({
          device_identifier: 'device-1',
          device_name: 'Updated Name',
        });
        expect(result).toBe(true);
      });
    });

    describe('deletePremiumDevice', () => {
      it('sends DELETE request with device_identifier in body', async () => {
        let capturedBody: unknown;

        server.use(
          http.delete(`${backendUrl}/api/1/premium/devices`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { deletePremiumDevice } = usePremiumDevicesApi();
        const result = await deletePremiumDevice('device-2');

        expect(capturedBody).toEqual({ device_identifier: 'device-2' });
        expect(result).toBe(true);
      });

      it('throws error on failure', async () => {
        server.use(
          http.delete(`${backendUrl}/api/1/premium/devices`, () =>
            HttpResponse.json({
              result: null,
              message: 'Device not found',
            }, { status: HTTPStatus.BAD_REQUEST })),
        );

        const { deletePremiumDevice } = usePremiumDevicesApi();

        await expect(deletePremiumDevice('invalid-device'))
          .rejects
          .toThrow();
      });
    });
  });
});
