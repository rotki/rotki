import type { ActionResult } from '@rotki/common';
import type { PremiumDevicesResponse } from '@/modules/premium/devices/premium';
import process from 'node:process';
import { http, HttpResponse } from 'msw';
import { type PremiumCapabilities, PremiumFeature } from '@/modules/session/types';

const backendUrl = process.env.VITE_BACKEND_URL;

const mockPremiumDevicesResponse: ActionResult<PremiumDevicesResponse> = {
  result: {
    currentDeviceId: 'test-device-123',
    devices: [
      {
        deviceIdentifier: 'test-device-123',
        deviceName: 'Test Device',
        lastSeenAt: 1700000000,
        platform: 'web',
        user: 'testuser',
      },
      {
        deviceIdentifier: 'device-456',
        deviceName: 'Another Device',
        lastSeenAt: 1699000000,
        platform: 'desktop',
        user: 'testuser',
      },
    ],
    limit: 5,
  },
  message: '',
};

const mockPremiumCapabilitiesResponse: ActionResult<PremiumCapabilities> = {
  result: {
    [PremiumFeature.ASSET_MOVEMENT_MATCHING]: { enabled: true, minimumTier: 'Free' },
    [PremiumFeature.ETH_STAKING_VIEW]: { enabled: true, minimumTier: 'Free' },
    [PremiumFeature.EVENT_ANALYSIS_VIEW]: { enabled: true, minimumTier: 'Free' },
    [PremiumFeature.GRAPHS_VIEW]: { enabled: true, minimumTier: 'Free' },
  },
  message: '',
};

export const premiumHandlers = [
  // GET /api/1/premium/capabilities
  http.get(`${backendUrl}/api/1/premium/capabilities`, () =>
    HttpResponse.json(mockPremiumCapabilitiesResponse, { status: 200 })),

  // GET /api/1/premium/devices
  http.get(`${backendUrl}/api/1/premium/devices`, () =>
    HttpResponse.json(mockPremiumDevicesResponse, { status: 200 })),

  // PATCH /api/1/premium/devices
  http.patch(`${backendUrl}/api/1/premium/devices`, () =>
    HttpResponse.json({ result: true, message: '' }, { status: 200 })),

  // DELETE /api/1/premium/devices
  http.delete(`${backendUrl}/api/1/premium/devices`, () =>
    HttpResponse.json({ result: true, message: '' }, { status: 200 })),
];
