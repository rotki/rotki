import type { ActionResult } from '@rotki/common';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus, validWithSessionStatus } from '@/services/utils';

interface GoogleCalendarStatus {
  authenticated: boolean;
}

interface GoogleCalendarDeviceInfo {
  verificationUrl: string;
  userCode: string;
  expiresIn: number;
}

interface GoogleCalendarSyncResult {
  success: boolean;
  calendar_id: string;
  events_processed: number;
  events_created: number;
  events_updated: number;
}

interface GoogleCalendarPollResult {
  success: boolean;
  pending?: boolean;
}

export function useGoogleCalendarApi(): {
  getStatus: () => Promise<GoogleCalendarStatus>;
  startAuth: (clientId: string, clientSecret: string) => Promise<GoogleCalendarDeviceInfo>;
  pollAuth: () => Promise<GoogleCalendarPollResult>;
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

  const startAuth = async (clientId: string, clientSecret: string): Promise<GoogleCalendarDeviceInfo> => {
    const response = await api.instance.put<ActionResult<GoogleCalendarDeviceInfo>>(
      '/calendar/google',
      {
        client_id: clientId,
        client_secret: clientSecret,
      },
      { validateStatus: validWithSessionStatus },
    );
    return handleResponse(response);
  };

  const pollAuth = async (): Promise<GoogleCalendarPollResult> => {
    console.log('pollAuth: Making PATCH request to /calendar/google');
    const response = await api.instance.patch<ActionResult<GoogleCalendarPollResult>>(
      '/calendar/google',
      { validateStatus: validWithSessionStatus },
    );
    console.log('pollAuth: Raw response:', response.data);
    const result = handleResponse(response);
    console.log('pollAuth: Processed result:', result);
    return result;
  };

  const syncCalendar = async (): Promise<GoogleCalendarSyncResult> => {
    const response = await api.instance.post<ActionResult<GoogleCalendarSyncResult>>(
      '/calendar/google',
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
    disconnect,
    getStatus,
    pollAuth,
    startAuth,
    syncCalendar,
  };
}
