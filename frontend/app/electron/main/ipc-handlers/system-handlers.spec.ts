// @vitest-environment node
import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import type { SettingsManager } from '@electron/main/settings-manager';
import process from 'node:process';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SystemHandlers } from './system-handlers';

const { openExternalMock } = vi.hoisted(() => ({
  openExternalMock: vi.fn<(url: string) => Promise<void>>(),
}));

vi.mock('electron', () => ({
  dialog: { showOpenDialog: vi.fn() },
  nativeTheme: {},
  shell: { openExternal: openExternalMock, openPath: vi.fn() },
}));

/**
 * The seam: `openUrl` either hands the url to the OS or rejects. The report issue
 * dialog keeps the user's draft whenever it rejects, so a refusal that resolved
 * quietly would lose the draft, which is what happened to every `mailto:` url.
 */
describe('systemHandlers.openUrl', () => {
  function createHandlers(isDev = false): SystemHandlers {
    const handlers = new SystemHandlers(
      createMock<LogService>(),
      createMock<SettingsManager>(),
      createMock<AppConfig>({ isDev }),
    );
    handlers.initialize({
      updateTray: vi.fn(),
      getProtocolRegistrationFailed: () => false,
      openOAuthInWindow: vi.fn(async (): Promise<void> => {}),
    });
    return handlers;
  }

  beforeEach(() => {
    // Electron adds this to `process`; node does not have it.
    process.getSystemVersion = (): string => '1.0.0';
    openExternalMock.mockReset();
    openExternalMock.mockResolvedValue(undefined);
  });

  it('should open a mailto url outside dev', async () => {
    const url = 'mailto:support@rotki.com?subject=hi&body=there';

    await createHandlers().openUrl(url);

    expect(openExternalMock).toHaveBeenCalledWith(url);
  });

  it('should open an https url outside dev', async () => {
    await createHandlers().openUrl('https://rotki.com');

    expect(openExternalMock).toHaveBeenCalledWith('https://rotki.com');
  });

  it('should reject any other scheme outside dev without opening it', async () => {
    await expect(createHandlers().openUrl('file:///etc/passwd')).rejects.toThrow('untrusted URL');

    expect(openExternalMock).not.toHaveBeenCalled();
  });

  it('should reject when the OS cannot open the url', async () => {
    openExternalMock.mockRejectedValue(new Error('no application registered for mailto'));

    await expect(createHandlers().openUrl('mailto:support@rotki.com')).rejects.toThrow('no application registered');
  });
});
