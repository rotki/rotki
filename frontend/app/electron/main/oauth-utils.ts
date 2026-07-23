import type { OAuthResult } from '@shared/ipc';

function parseSuccessCallback(callbackUrl: URL): OAuthResult {
  const accessToken = callbackUrl.searchParams.get('access_token');
  if (!accessToken) {
    return {
      success: false,
      service: callbackUrl.searchParams.get('service') ?? 'unknown',
      error: new Error('Failed to parse OAuth callback URL. missing access_token'),
    };
  }

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

function parseFailureCallback(callbackUrl: URL): OAuthResult | undefined {
  const errorMessage = callbackUrl.searchParams.get('error');
  if (!errorMessage)
    return undefined;

  return {
    success: false,
    service: callbackUrl.searchParams.get('service') ?? 'unknown',
    error: new Error(errorMessage),
  };
}

export function parseToken(oAuthUrl: string): OAuthResult {
  // Parse the OAuth callback URL
  try {
    const callbackUrl = new URL(oAuthUrl);

    if (callbackUrl.pathname === '/success')
      return parseSuccessCallback(callbackUrl);

    if (callbackUrl.pathname === '/failure') {
      const failure = parseFailureCallback(callbackUrl);
      if (failure)
        return failure;
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
