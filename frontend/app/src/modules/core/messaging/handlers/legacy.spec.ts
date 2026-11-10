import type { useInterop } from '@/modules/shell/app/use-electron-interop';
import { assert, Severity } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { mockT } from '@test/i18n';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createLegacyHandler } from '@/modules/core/messaging/handlers/legacy';
import { MESSAGE_WARNING } from '@/modules/core/messaging/types/base';

const { mockOpenUrl } = vi.hoisted(() => ({ mockOpenUrl: vi.fn<(url: string) => Promise<void>>() }));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: vi.fn(() => createMock<ReturnType<typeof useInterop>>({ openUrl: mockOpenUrl })),
}));

describe('createLegacyHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show a device limit warning as premium deactivated, without the marker and with a manage devices action', async () => {
    const handler = createLegacyHandler(mockT);
    const result = await handler.handle({
      value: 'Error: Device limit of 3 exceeded _DEVICE_LIMIT_LINK_. Check logs for more details',
      verbosity: MESSAGE_WARNING,
    });

    expect(result.message).toBe('Error: Device limit of 3 exceeded. Check logs for more details');
    expect(result.title).toBe('notification_messages.premium.inactive.title');
    expect(result.display).toBe(true);
    expect(result.severity).toBe(Severity.ERROR);
    assert(result.action && !Array.isArray(result.action));

    await result.action.action();
    expect(mockOpenUrl).toHaveBeenCalledWith(externalLinks.premiumDevices);
  });

  it('should keep other warnings silent and without an action', async () => {
    const handler = createLegacyHandler(mockT);
    const result = await handler.handle({ value: 'Some warning', verbosity: MESSAGE_WARNING });

    expect(result.message).toBe('Some warning');
    expect(result.title).toBe('notification_messages.backend.warning_title');
    expect(result.severity).toBe(Severity.WARNING);
    expect(result.display).toBe(false);
    expect(result.action).toBeUndefined();
  });

  it('should show errors without an action', async () => {
    const handler = createLegacyHandler(mockT);
    const result = await handler.handle({ value: 'Some error', verbosity: 'error' });

    expect(result.display).toBe(true);
    expect(result.severity).toBe(Severity.ERROR);
    expect(result.action).toBeUndefined();
  });
});
