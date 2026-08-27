import type { GoogleCalendarAuthResult, GoogleCalendarStatus, GoogleCalendarSyncResult } from '@/modules/settings/types/google-calendar';
import { Severity } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGoogleCalendarIntegration } from '@/modules/calendar/use-google-calendar-integration';

const notify = vi.fn();
vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: (): { notify: typeof notify } => ({ notify }),
}));

const completeOAuth = vi.fn<(accessToken: string, refreshToken: string) => Promise<GoogleCalendarAuthResult>>();
const disconnectApi = vi.fn<() => Promise<{ success: boolean }>>();
const getStatus = vi.fn<() => Promise<GoogleCalendarStatus>>();
const syncCalendar = vi.fn<() => Promise<GoogleCalendarSyncResult>>();

const calendarApi = { completeOAuth, disconnect: disconnectApi, getStatus, syncCalendar };

vi.mock('@/modules/settings/api/use-google-calendar-api', () => ({
  useGoogleCalendarApi: (): typeof calendarApi => calendarApi,
}));

const { interop, openUrl } = vi.hoisted(() => {
  const openUrl = vi.fn<(url: string) => Promise<void>>();
  return { interop: { isPackaged: false, openUrl }, openUrl };
});

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): typeof interop => interop,
}));

describe('useGoogleCalendarIntegration', () => {
  let calendar: ReturnType<typeof useGoogleCalendarIntegration>;

  /** `isPackaged` is read when the composable is created, so it has to be set before that. */
  function usePackagedApp(): ReturnType<typeof useGoogleCalendarIntegration> {
    interop.isPackaged = true;
    return useGoogleCalendarIntegration();
  }

  beforeEach(() => {
    vi.clearAllMocks();
    interop.isPackaged = false;
    getStatus.mockResolvedValue({ authenticated: false });
    completeOAuth.mockResolvedValue({ message: 'connected', success: true, userEmail: 'someone@example.com' });
    syncCalendar.mockResolvedValue({ calendarId: 'primary', eventsCreated: 0, eventsProcessed: 0, eventsUpdated: 0 });
    disconnectApi.mockResolvedValue({ success: true });
    calendar = useGoogleCalendarIntegration();
  });

  describe('checkStatus', () => {
    it('should take the account the backend reports', async () => {
      getStatus.mockResolvedValue({ authenticated: true, userEmail: 'someone@example.com' });

      await calendar.checkStatus();

      expect(get(calendar.isConnected)).toBe(true);
      expect(get(calendar.connectedUserEmail)).toBe('someone@example.com');
    });

    it('should forget the account when the backend reports none', async () => {
      getStatus.mockResolvedValue({ authenticated: false, userEmail: 'stale@example.com' });

      await calendar.checkStatus();

      expect(get(calendar.isConnected)).toBe(false);
      expect(get(calendar.connectedUserEmail)).toBe('');
    });

    it('should stay quiet when the status cannot be read', async () => {
      getStatus.mockRejectedValue(new Error('offline'));

      await calendar.checkStatus();

      expect(get(calendar.isConnected)).toBe(false);
      expect(notify).not.toHaveBeenCalled();
    });
  });

  describe('connect', () => {
    it('should hand the consent page to the desktop browser when packaged', async () => {
      calendar = usePackagedApp();

      await calendar.connect();

      expect(openUrl).toHaveBeenCalledWith(expect.stringContaining('/oauth/google?mode=app'));
      // Still authorizing: the packaged app waits for the tokens to come back over IPC.
      expect(get(calendar.isAuthorizing)).toBe(true);
      expect(get(calendar.showTokenInput)).toBe(false);
    });

    it('should ask for the tokens by hand when there is no callback channel', async () => {
      const open = vi.spyOn(window, 'open').mockReturnValue(null);

      await calendar.connect();

      expect(open).toHaveBeenCalledWith(expect.stringContaining('/oauth/google?mode=docker'), '_blank');
      expect(get(calendar.showTokenInput)).toBe(true);
      expect(get(calendar.isAuthorizing)).toBe(false);
      expect(openUrl).not.toHaveBeenCalled();
    });

    it('should report a failure to open the consent page and stop authorizing', async () => {
      calendar = usePackagedApp();
      openUrl.mockRejectedValue(new Error('no browser'));

      await calendar.connect();

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({ message: 'no browser', severity: Severity.ERROR }));
      expect(get(calendar.isAuthorizing)).toBe(false);
    });
  });

  describe('handleOAuthCallback', () => {
    it('should ignore a callback for another service', async () => {
      await calendar.handleOAuthCallback({ accessToken: 'a', refreshToken: 'r', service: 'monerium', success: true });

      expect(completeOAuth).not.toHaveBeenCalled();
    });

    it('should complete the authorization and re-read the status', async () => {
      getStatus.mockResolvedValue({ authenticated: true, userEmail: 'someone@example.com' });

      await calendar.handleOAuthCallback({ accessToken: 'a', refreshToken: 'r', service: 'google', success: true });

      expect(completeOAuth).toHaveBeenCalledWith('a', 'r');
      expect(getStatus).toHaveBeenCalledOnce();
      expect(get(calendar.isConnected)).toBe(true);
      expect(get(calendar.connectedUserEmail)).toBe('someone@example.com');
      expect(get(calendar.isAuthorizing)).toBe(false);
    });

    it('should report the error a failed callback carries', async () => {
      await calendar.handleOAuthCallback({ error: new Error('denied'), service: 'google', success: false });

      expect(completeOAuth).not.toHaveBeenCalled();
      expect(notify).toHaveBeenCalledWith(expect.objectContaining({ message: 'denied', severity: Severity.ERROR }));
    });

    it('should refuse a success without a refresh token', async () => {
      await calendar.handleOAuthCallback({ accessToken: 'a', service: 'google', success: true });

      expect(completeOAuth).not.toHaveBeenCalled();
      expect(notify).toHaveBeenCalledWith(expect.objectContaining({
        message: 'external_services.google_calendar.auth_failed',
      }));
    });

    it('should report a rejected exchange and stop authorizing', async () => {
      completeOAuth.mockRejectedValue(new Error('backend said no'));

      await calendar.handleOAuthCallback({ accessToken: 'a', refreshToken: 'r', service: 'google', success: true });

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({ message: 'backend said no' }));
      expect(get(calendar.isConnected)).toBe(false);
      expect(get(calendar.isAuthorizing)).toBe(false);
    });

    it('should not connect when the exchange itself reports failure', async () => {
      completeOAuth.mockResolvedValue({ message: 'token rejected', success: false });

      await calendar.handleOAuthCallback({ accessToken: 'a', refreshToken: 'r', service: 'google', success: true });

      expect(get(calendar.isConnected)).toBe(false);
      expect(notify).toHaveBeenCalledWith(expect.objectContaining({ severity: Severity.ERROR }));
    });
  });

  describe('submitManualToken', () => {
    it('should refuse a blank access token', async () => {
      set(calendar.modelManualToken, '   ');

      await calendar.submitManualToken();

      expect(completeOAuth).not.toHaveBeenCalled();
      expect(notify).toHaveBeenCalledWith(expect.objectContaining({
        message: 'external_services.google_calendar.token_required',
      }));
    });

    it('should send the trimmed tokens and put the form away', async () => {
      set(calendar.modelManualToken, '  access  ');
      set(calendar.modelManualRefreshToken, '  refresh  ');

      await calendar.submitManualToken();

      expect(completeOAuth).toHaveBeenCalledWith('access', 'refresh');
      expect(get(calendar.modelManualToken)).toBe('');
      expect(get(calendar.showTokenInput)).toBe(false);
      expect(get(calendar.isAuthorizing)).toBe(false);
    });
  });

  describe('sync', () => {
    it('should say what was synced', async () => {
      syncCalendar.mockResolvedValue({ calendarId: 'primary', eventsCreated: 2, eventsProcessed: 3, eventsUpdated: 1 });

      await calendar.sync();

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({
        message: expect.stringContaining('external_services.google_calendar.sync_complete'),
        severity: Severity.INFO,
      }));
      expect(get(calendar.isSyncing)).toBe(false);
    });

    it('should say when there was nothing to sync', async () => {
      await calendar.sync();

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({
        message: 'external_services.google_calendar.no_events_to_sync',
      }));
    });

    it('should report a failed sync and stop syncing', async () => {
      syncCalendar.mockRejectedValue(new Error('sync broke'));

      await calendar.sync();

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({ message: 'sync broke', severity: Severity.ERROR }));
      expect(get(calendar.isSyncing)).toBe(false);
    });
  });

  describe('disconnect', () => {
    it('should forget the connection', async () => {
      getStatus.mockResolvedValue({ authenticated: true, userEmail: 'someone@example.com' });
      await calendar.checkStatus();

      await calendar.disconnect();

      expect(get(calendar.isConnected)).toBe(false);
      expect(get(calendar.connectedUserEmail)).toBe('');
    });

    it('should keep the connection when disconnecting fails', async () => {
      getStatus.mockResolvedValue({ authenticated: true, userEmail: 'someone@example.com' });
      await calendar.checkStatus();
      disconnectApi.mockRejectedValue(new Error('still connected'));

      await calendar.disconnect();

      expect(get(calendar.isConnected)).toBe(true);
      expect(notify).toHaveBeenCalledWith(expect.objectContaining({ message: 'still connected' }));
    });
  });
});
