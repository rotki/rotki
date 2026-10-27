import type { OAuthResult } from '@shared/ipc';
import type { Ref } from 'vue';
import { NotificationKind, Severity } from '@rotki/common';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useGoogleCalendarApi } from '@/modules/settings/api/use-google-calendar-api';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

interface UseGoogleCalendarIntegrationReturn {
  /** Both bound with `v-model` by the manual token fields, so they stay writable. */
  modelManualToken: Ref<string>;
  modelManualRefreshToken: Ref<string>;
  isConnected: Readonly<Ref<boolean>>;
  isSyncing: Readonly<Ref<boolean>>;
  isAuthorizing: Readonly<Ref<boolean>>;
  /** The account the backend reports, empty when it reports none. */
  connectedUserEmail: Readonly<Ref<string>>;
  /** Only the packaged app gets the tokens back over IPC; elsewhere they are pasted in. */
  showTokenInput: Readonly<Ref<boolean>>;
  /**
   * What the last authorization, sync or disconnect failed with, for the card to name: on the token
   * field while the token form is open, otherwise in the card. Cleared when the next one starts.
   */
  failure: Readonly<Ref<string | undefined>>;
  checkStatus: () => Promise<void>;
  connect: () => Promise<void>;
  cancelAuthorization: () => void;
  /** Handed to the backend message bus, which calls it for every service. */
  handleOAuthCallback: (oAuthResult: OAuthResult) => Promise<void>;
  submitManualToken: () => Promise<void>;
  cancelTokenInput: () => void;
  sync: () => Promise<void>;
  disconnect: () => Promise<void>;
}

/**
 * Connecting rotki to a Google calendar, and syncing to it.
 *
 * The authorization has two shapes. The packaged app opens the consent page in the system browser
 * and is handed the tokens back over IPC, so `handleOAuthCallback` finishes the job. Anywhere else
 * (docker, web) there is no callback channel: the page opens in a tab and the user pastes the two
 * tokens in, which takes the same path with a hand-made success result.
 */
export function useGoogleCalendarIntegration(): UseGoogleCalendarIntegrationReturn {
  const websiteUrl = import.meta.env.VITE_ROTKI_WEBSITE_URL;

  const { t } = useI18n({ useScope: 'global' });
  const { completeOAuth, disconnect: disconnectApi, getStatus, syncCalendar } = useGoogleCalendarApi();
  const { notify } = useNotificationDispatcher();
  const { isPackaged, openUrl } = useInterop();

  const isConnected = shallowRef<boolean>(false);
  const isSyncing = shallowRef<boolean>(false);
  const isAuthorizing = shallowRef<boolean>(false);
  const connectedUserEmail = shallowRef<string>('');
  const showTokenInput = shallowRef<boolean>(false);
  const modelManualToken = shallowRef<string>('');
  const modelManualRefreshToken = shallowRef<string>('');
  const failure = shallowRef<string>();

  /** Keeps why an action failed, for the card to name, and logs it. */
  function fail(error: unknown, fallback: string): void {
    logger.error('Google Calendar action failed:', error);
    set(failure, getErrorMessage(error) || fallback);
  }

  async function checkStatus(): Promise<void> {
    try {
      const response = await getStatus();
      set(isConnected, response.authenticated);
      set(connectedUserEmail, response.authenticated ? response.userEmail ?? '' : '');
    }
    catch (error: unknown) {
      logger.error('Failed to check Google Calendar status:', error);
    }
  }

  async function connect(): Promise<void> {
    set(isAuthorizing, true);
    set(failure, undefined);
    try {
      const oauthUrl = `${websiteUrl}/oauth/google?mode=${isPackaged ? 'app' : 'docker'}`;

      if (isPackaged) {
        await openUrl(oauthUrl);
      }
      else if (typeof window !== 'undefined') {
        // No callback channel outside the packaged app, so the tokens come back by hand.
        window.open(oauthUrl, '_blank');
        set(isAuthorizing, false);
        set(showTokenInput, true);
      }

      notify({ message: t('external_services.google_calendar.opening_browser'), kind: NotificationKind.RESULT, severity: Severity.INFO, title: t('external_services.google_calendar.authorizing') });
    }
    catch (error: unknown) {
      fail(error, t('external_services.google_calendar.auth_failed'));
      set(isAuthorizing, false);
    }
  }

  function cancelAuthorization(): void {
    set(isAuthorizing, false);
  }

  /**
   * Hands the tokens to the backend.
   *
   * @returns whether rotki is now connected, so a pasted token is only cleared once it worked
   */
  async function completeAuthorization(oAuthResult: OAuthResult): Promise<boolean> {
    set(failure, undefined);
    try {
      if (!oAuthResult.success) {
        fail(oAuthResult.error, t('external_services.google_calendar.auth_failed'));
        return false;
      }

      const { accessToken, refreshToken } = oAuthResult;
      if (!refreshToken) {
        set(failure, t('external_services.google_calendar.auth_failed'));
        return false;
      }

      const result = await completeOAuth(accessToken, refreshToken);
      logger.debug('received oauth result', result);

      if (!result.success) {
        fail(result, t('external_services.google_calendar.auth_failed'));
        return false;
      }

      set(isConnected, true);
      set(connectedUserEmail, result.userEmail ?? '');
      await checkStatus();
      return true;
    }
    catch (error: unknown) {
      fail(error, t('external_services.google_calendar.auth_failed'));
      return false;
    }
    finally {
      set(isAuthorizing, false);
    }
  }

  async function handleOAuthCallback(oAuthResult: OAuthResult): Promise<void> {
    if (oAuthResult.service === 'google')
      await completeAuthorization(oAuthResult);
  }

  async function submitManualToken(): Promise<void> {
    const accessToken = get(modelManualToken).trim();
    if (!accessToken) {
      set(failure, t('external_services.google_calendar.token_required'));
      return;
    }

    set(isAuthorizing, true);
    const connected = await completeAuthorization({
      accessToken,
      refreshToken: get(modelManualRefreshToken).trim(),
      service: 'google',
      success: true,
    });
    if (connected)
      cancelTokenInput();
  }

  function cancelTokenInput(): void {
    set(modelManualToken, '');
    set(modelManualRefreshToken, '');
    set(failure, undefined);
    set(showTokenInput, false);
  }

  async function sync(): Promise<void> {
    set(isSyncing, true);
    set(failure, undefined);
    try {
      const result = await syncCalendar();

      notify({
        message: result.eventsProcessed === 0
          ? t('external_services.google_calendar.no_events_to_sync')
          : t('external_services.google_calendar.sync_complete', {
              created: result.eventsCreated || 0,
              total: result.eventsProcessed || 0,
              updated: result.eventsUpdated || 0,
            }),
        kind: NotificationKind.RESULT,
        severity: Severity.INFO,
        title: t('external_services.google_calendar.success'),
      });
    }
    catch (error: unknown) {
      fail(error, t('external_services.google_calendar.sync_failed'));
    }
    finally {
      set(isSyncing, false);
    }
  }

  async function disconnect(): Promise<void> {
    set(failure, undefined);
    try {
      await disconnectApi();
      set(isConnected, false);
      set(connectedUserEmail, '');
    }
    catch (error: unknown) {
      fail(error, t('external_services.google_calendar.disconnect_failed'));
    }
  }

  return {
    cancelAuthorization,
    cancelTokenInput,
    checkStatus,
    connect,
    connectedUserEmail: readonly(connectedUserEmail),
    disconnect,
    failure: readonly(failure),
    handleOAuthCallback,
    isAuthorizing: readonly(isAuthorizing),
    isConnected: readonly(isConnected),
    isSyncing: readonly(isSyncing),
    modelManualRefreshToken,
    modelManualToken,
    showTokenInput: readonly(showTokenInput),
    submitManualToken,
    sync,
  };
}
