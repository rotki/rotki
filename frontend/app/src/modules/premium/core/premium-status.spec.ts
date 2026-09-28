import { describe, expect, it } from 'vitest';
import { PremiumInactiveCause } from '@/modules/shell/action-center/use-raised-conditions-store';
import { readPremiumStatus } from './premium-status';

describe('modules/premium/core/premium-status', () => {
  it('should read an active status as active, whatever else it carries', () => {
    expect(readPremiumStatus({ expired: true, isPremiumActive: true, reason: 'ignored' })).toEqual({ active: true });
  });

  it('should read a rejected key as expired', () => {
    expect(readPremiumStatus({ expired: true, isPremiumActive: false })).toEqual({ active: false, cause: PremiumInactiveCause.EXPIRED });
  });

  it('should read a status with a reason as the device limit, keeping the backend explanation', () => {
    expect(readPremiumStatus({ expired: false, isPremiumActive: false, reason: 'All 3 devices are in use' }))
      .toEqual({ active: false, cause: PremiumInactiveCause.DEVICE_LIMIT, reason: 'All 3 devices are in use' });
  });

  it('should read a status with neither as an unreachable server', () => {
    expect(readPremiumStatus({ expired: false, isPremiumActive: false })).toEqual({ active: false, cause: PremiumInactiveCause.UNREACHABLE });
  });
});
