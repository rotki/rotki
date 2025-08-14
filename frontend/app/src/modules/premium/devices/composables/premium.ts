import { z } from 'zod/v4';

export const PremiumDevice = z.object({
  deviceIdentifier: z.string(),
  deviceName: z.string(),
  lastSeenAt: z.number(),
  platform: z.string(),
  user: z.string(),
});

export type PremiumDevice = z.infer<typeof PremiumDevice>;

export const PremiumDevicesResponse = z.object({
  currentDeviceId: z.string(),
  devices: z.array(PremiumDevice),
  limit: z.number(),
});

export type PremiumDevicesResponse = z.infer<typeof PremiumDevicesResponse>;

export interface PremiumDevicePayload {
  deviceIdentifier: string;
  deviceName: string;
}
