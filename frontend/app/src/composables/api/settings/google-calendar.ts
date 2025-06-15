import { api } from '@/services/rotkehlchen-api';

interface GoogleCalendarStatus {
  authenticated: boolean;
}

interface GoogleCalendarAuthResponse {
  auth_url: string;
}

interface GoogleCalendarSyncResult {
  success: boolean;
  calendar_id: string;
  events_processed: number;
  events_created: number;
  events_updated: number;
}

export function useGoogleCalendarApi(): {
  getStatus: () => Promise<GoogleCalendarStatus>;
  startAuth: (clientId: string, clientSecret: string) => Promise<GoogleCalendarAuthResponse>;
  completeAuth: (authResponseUrl: string) => Promise<{ success: boolean }>;
  syncCalendar: () => Promise<GoogleCalendarSyncResult>;
  disconnect: () => Promise<{ success: boolean }>;
} {
  const getStatus = async (): Promise<GoogleCalendarStatus> => {
    const response = await api.instance.get<GoogleCalendarStatus>('/calendar/google');
    return response.data;
  };

  const startAuth = async (clientId: string, clientSecret: string): Promise<GoogleCalendarAuthResponse> => {
    const response = await api.instance.put<GoogleCalendarAuthResponse>(
      '/calendar/google',
      {
        client_id: clientId,
        client_secret: clientSecret,
      },
    );
    return response.data;
  };

  const completeAuth = async (authResponseUrl: string): Promise<{ success: boolean }> => {
    const response = await api.instance.patch<{ success: boolean }>(
      '/calendar/google',
      {
        auth_response_url: authResponseUrl,
      },
    );
    return response.data;
  };

  const syncCalendar = async (): Promise<GoogleCalendarSyncResult> => {
    const response = await api.instance.post<GoogleCalendarSyncResult>('/calendar/google');
    return response.data;
  };

  const disconnect = async (): Promise<{ success: boolean }> => {
    const response = await api.instance.delete<{ success: boolean }>('/calendar/google');
    return response.data;
  };

  return {
    completeAuth,
    disconnect,
    getStatus,
    startAuth,
    syncCalendar,
  };
}
