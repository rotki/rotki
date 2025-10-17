import type { OAuthResult } from '@shared/ipc';

export function parseToken(oAuthUrl: string): OAuthResult {
  // Parse the OAuth callback URL
  try {
    const callbackUrl = new URL(oAuthUrl);

    if (callbackUrl.pathname === '/success') {
      const accessToken = callbackUrl.searchParams.get('access_token');
      if (accessToken) {
        const refreshToken = callbackUrl.searchParams.get('refresh_token') ?? undefined;
        const service = callbackUrl.searchParams.get('service') ?? 'google';
        const expiresInRaw = callbackUrl.searchParams.get('expires_in');
        const expiresIn = expiresInRaw ? Number.parseInt(expiresInRaw, 10) : undefined;
        return {
          success: true,
          service,
          accessToken,
          refreshToken,
          expiresIn: Number.isNaN(expiresIn) ? undefined : expiresIn,
        };
      }
      else {
        const service = callbackUrl.searchParams.get('service') ?? 'unknown';
        return {
          success: false,
          service,
          error: new Error('Failed to parse OAuth callback URL. missing access_token'),
        };
      }
    }
    else if (callbackUrl.pathname === '/failure') {
      const errorMessage = callbackUrl.searchParams.get('error');
      if (errorMessage) {
        const service = callbackUrl.searchParams.get('service') ?? 'unknown';
        return {
          success: false,
          service,
          error: new Error(errorMessage),
        };
      }
    }
  }
  catch (parseError: any) {
    return {
      success: false,
      service: 'unknown',
      error: new Error(`Failed to parse OAuth callback URL: ${parseError.message}`),
    };
  }
  return {
    success: false,
    service: 'unknown',
    error: new Error(`Invalid path in OAuth callback URL: ${oAuthUrl}`),
  };
}
