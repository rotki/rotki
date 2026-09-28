import { mockT } from '@test/i18n';
import { beforeEach, describe, expect, it } from 'vitest';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { PremiumInactiveCause, RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';
import { createPremiumStatusHandler } from './premium-status';

describe('modules/core/messaging/handlers/premium-status', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should raise the premium row, with no notification, when a saved key stops working', async () => {
    usePremiumStore().premium = true;

    const notification = await createPremiumStatusHandler(mockT).handle({ expired: true, isPremiumActive: false });

    expect(notification).toBeNull();
    expect(usePremiumStore().premium).toBe(false);
    expect(useRaisedConditionsStore().conditions).toEqual([{ cause: PremiumInactiveCause.EXPIRED, kind: RaisedConditionKind.PREMIUM_INACTIVE, reason: undefined }]);
  });

  it('should raise the row for a session that started without working premium, on the hourly check', async () => {
    await createPremiumStatusHandler(mockT).handle({ expired: false, isPremiumActive: false });

    expect(useRaisedConditionsStore().conditions).toEqual([{ cause: PremiumInactiveCause.UNREACHABLE, kind: RaisedConditionKind.PREMIUM_INACTIVE, reason: undefined }]);
  });

  it('should keep one row across repeated checks, carrying the latest cause', async () => {
    const handler = createPremiumStatusHandler(mockT);
    await handler.handle({ expired: false, isPremiumActive: false });
    await handler.handle({ expired: false, isPremiumActive: false, reason: 'All devices in use' });

    expect(useRaisedConditionsStore().conditions).toEqual([{ cause: PremiumInactiveCause.DEVICE_LIMIT, kind: RaisedConditionKind.PREMIUM_INACTIVE, reason: 'All devices in use' }]);
  });

  it('should take the row down and announce premium once a check finds the key working again', async () => {
    const handler = createPremiumStatusHandler(mockT);
    await handler.handle({ expired: true, isPremiumActive: false });

    const notification = await handler.handle({ expired: false, isPremiumActive: true });

    expect(useRaisedConditionsStore().conditions).toEqual([]);
    expect(usePremiumStore().premium).toBe(true);
    expect(notification).toEqual(expect.objectContaining({ title: 'notification_messages.premium.active.title' }));
  });

  it('should stay quiet on an hourly check that finds premium still working', async () => {
    usePremiumStore().premium = true;

    expect(await createPremiumStatusHandler(mockT).handle({ expired: false, isPremiumActive: true })).toBeNull();
  });
});
