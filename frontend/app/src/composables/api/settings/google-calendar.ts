import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/api/utils';
import {
  type GoogleCalendarAuthResult,
  GoogleCalendarAuthResultSchema,
  type GoogleCalendarDisconnectResult,
  GoogleCalendarDisconnectResultSchema,
  type GoogleCalendarStatus,
  GoogleCalendarStatusSchema,
  type GoogleCalendarSyncResult,
  GoogleCalendarSyncResultSchema,
} from '@/types/settings/google-calendar';

export function useGoogleCalendarApi(): {
  getStatus: () => Promise<GoogleCalendarStatus>;
  completeOAuth: (accessToken: string, refreshToken: string) => Promise<GoogleCalendarAuthResult>;
  syncCalendar: () => Promise<GoogleCalendarSyncResult>;
  disconnect: () => Promise<GoogleCalendarDisconnectResult>;
} {
  const getStatus = async (): Promise<GoogleCalendarStatus> => {
    const response = await api.get<GoogleCalendarStatus>(
      '/calendar/google',
      { validStatuses: VALID_WITH_SESSION_STATUS },
    );
    return GoogleCalendarStatusSchema.parse(response);
  };

  const syncCalendar = async (): Promise<GoogleCalendarSyncResult> => {
    const response = await api.post<GoogleCalendarSyncResult>(
      '/calendar/google',
      undefined,
      { validStatuses: VALID_WITH_SESSION_STATUS },
    );
    return GoogleCalendarSyncResultSchema.parse(response);
  };

  const completeOAuth = async (accessToken: string, refreshToken: string): Promise<GoogleCalendarAuthResult> => {
    const response = await api.put<GoogleCalendarAuthResult>(
      '/calendar/google',
      { accessToken, refreshToken },
      { validStatuses: VALID_WITH_SESSION_STATUS },
    );
    return GoogleCalendarAuthResultSchema.parse(response);
  };

  const disconnect = async (): Promise<GoogleCalendarDisconnectResult> => {
    const response = await api.delete<GoogleCalendarDisconnectResult>(
      '/calendar/google',
      { validStatuses: VALID_WITH_SESSION_STATUS },
    );
    return GoogleCalendarDisconnectResultSchema.parse(response);
  };

  return {
    completeOAuth,
    disconnect,
    getStatus,
    syncCalendar,
  };
}
