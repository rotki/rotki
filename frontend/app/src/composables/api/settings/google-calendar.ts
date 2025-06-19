import type { ActionResult } from '@rotki/common';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithSessionStatus } from '@/services/utils';

interface GoogleCalendarStatus {
  authenticated: boolean;
  userEmail?: string;
}

interface GoogleCalendarFlowStatus {
  status: string;
  message: string;
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
  startAuth: () => Promise<GoogleCalendarFlowStatus>;
  runAuth: () => Promise<GoogleCalendarAuthResult>;
  completeOAuth: (accessToken: string) => Promise<GoogleCalendarAuthResult>;
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

  const startAuth = async (): Promise<GoogleCalendarFlowStatus> => {
    const response = await api.instance.put<ActionResult<GoogleCalendarFlowStatus>>(
      '/calendar/google',
      {},
      { validateStatus: validWithSessionStatus },
    );
    return handleResponse(response);
  };

  const runAuth = async (): Promise<GoogleCalendarAuthResult> => {
    const response = await api.instance.patch<ActionResult<GoogleCalendarAuthResult>>(
      '/calendar/google',
      {},
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

  const completeOAuth = async (accessToken: string): Promise<GoogleCalendarAuthResult> => {
    const response = await api.instance.post<ActionResult<GoogleCalendarAuthResult>>(
      '/calendar/google/complete-oauth',
      { access_token: accessToken },
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
    runAuth,
    startAuth,
    syncCalendar,
  };
}
