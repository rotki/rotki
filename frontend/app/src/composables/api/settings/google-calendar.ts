import type { ActionResult } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithSessionStatus } from '@/services/utils';

interface GoogleCalendarStatus {
  authenticated: boolean;
  userEmail?: string;
}

interface GoogleCalendarAuthResult {
  success: boolean;
  message: string;
  userEmail?: string;
}

interface GoogleCalendarSyncResult {
  success: boolean;
  calendarId: string;
  eventsProcessed: number;
  eventsCreated: number;
  eventsUpdated: number;
}

export function useGoogleCalendarApi(): {
  getStatus: () => Promise<GoogleCalendarStatus>;
  completeOAuth: (accessToken: string, refreshToken: string) => Promise<GoogleCalendarAuthResult>;
  syncCalendar: () => Promise<GoogleCalendarSyncResult>;
  disconnect: () => Promise<{ success: boolean }>;
} {
  const getStatus = async (): Promise<GoogleCalendarStatus> => {
    const response = await api.instance.get<ActionResult<GoogleCalendarStatus>>(
      '/calendar/google',
      { validateStatus: validWithSessionStatus },
    );
    return handleResponse(response);
  };

  const syncCalendar = async (): Promise<GoogleCalendarSyncResult> => {
    const response = await api.instance.post<ActionResult<GoogleCalendarSyncResult>>(
      '/calendar/google',
      { validateStatus: validWithSessionStatus },
    );
    return handleResponse(response);
  };

  const completeOAuth = async (accessToken: string, refreshToken: string): Promise<GoogleCalendarAuthResult> => {
    const response = await api.instance.put<ActionResult<GoogleCalendarAuthResult>>(
      '/calendar/google',
      snakeCaseTransformer({ accessToken, refreshToken }),
      { validateStatus: validWithSessionStatus },
    );
    return handleResponse(response);
  };

  const disconnect = async (): Promise<{ success: boolean }> => {
    const response = await api.instance.delete<ActionResult<{ success: boolean }>>(
      '/calendar/google',
      { validateStatus: validWithSessionStatus },
    );
    return handleResponse(response);
  };

  return {
    completeOAuth,
    disconnect,
    getStatus,
    syncCalendar,
  };
}
