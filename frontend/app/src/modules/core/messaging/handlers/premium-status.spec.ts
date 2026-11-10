import type { useInterop } from '@/modules/shell/app/use-electron-interop';
import { assert, Severity } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { mockT } from '@test/i18n';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPremiumStatusHandler } from '@/modules/core/messaging/handlers/premium-status';

const { mockOpenUrl, premium } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { mockOpenUrl: vi.fn<(url: string) => Promise<void>>(), premium: ref<boolean>(true) };
});

vi.mock('@/modules/premium/use-premium', () => ({
  usePremium: vi.fn(() => premium),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: vi.fn(() => createMock<ReturnType<typeof useInterop>>({ openUrl: mockOpenUrl })),
}));

describe('createPremiumStatusHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(premium, true);
  });

  it('should show the device limit reason with a manage devices action', async () => {
    const handler = createPremiumStatusHandler(mockT);
    const result = await handler.handle({ expired: false, isPremiumActive: false, reason: 'Device limit of 3 exceeded' });

    assert(result);
    expect(result.severity).toBe(Severity.ERROR);
    expect(result.message).toBe('Device limit of 3 exceeded');
    assert(result.action && !Array.isArray(result.action));
    expect(result.action.label).toBe('notification_messages.premium.inactive.manage_devices');

    await result.action.action();
    expect(mockOpenUrl).toHaveBeenCalledWith(externalLinks.premiumDevices);
  });

  it('should not offer to manage devices when premium expired', async () => {
    const handler = createPremiumStatusHandler(mockT);
    const result = await handler.handle({ expired: true, isPremiumActive: false });

    assert(result);
    expect(result.message).toBe('notification_messages.premium.inactive.expired_message');
    expect(result.action).toBeUndefined();
  });

  it('should not offer to manage devices on a network problem', async () => {
    const handler = createPremiumStatusHandler(mockT);
    const result = await handler.handle({ expired: false, isPremiumActive: false });

    assert(result);
    expect(result.message).toBe('notification_messages.premium.inactive.network_problem_message');
    expect(result.action).toBeUndefined();
  });

  it('should stay silent when premium was already off', async () => {
    set(premium, false);
    const handler = createPremiumStatusHandler(mockT);

    expect(await handler.handle({ expired: false, isPremiumActive: false, reason: 'Device limit of 3 exceeded' })).toBeNull();
  });
});
