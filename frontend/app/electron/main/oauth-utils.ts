import type { OAuthResult } from '@shared/ipc';

export function parseToken(oAuthUrl: string): OAuthResult {
  // Parse the OAuth callback URL
  try {
    const callbackUrl = new URL(oAuthUrl);

    if (callbackUrl.pathname === '/success') {
      const accessToken = callbackUrl.searchParams.get('access_token');
      const refreshToken = callbackUrl.searchParams.get('refresh_token');
      if (accessToken && refreshToken) {
        return {
          success: true,
          accessToken,
          refreshToken,
        };
      }
      else {
        return {
          success: false,
          error: new Error('Failed to parse OAuth callback URL. missing access_token or refresh_token'),
        };
      }
    }
    else if (callbackUrl.pathname === '/failure') {
      const errorMessage = callbackUrl.searchParams.get('error');
      if (errorMessage) {
        return {
          success: false,
          error: new Error(errorMessage),
        };
      }
    }
  }
  catch (parseError: any) {
    return {
      success: false,
      error: new Error(`Failed to parse OAuth callback URL: ${parseError.message}`),
    };
  }
  return {
    success: false,
    error: new Error(`Invalid path in OAuth callback URL: ${oAuthUrl}`),
  };
}
