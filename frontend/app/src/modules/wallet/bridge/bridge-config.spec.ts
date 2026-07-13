import { describe, expect, it } from 'vitest';
import { CLIENT_CONFIG, PROXY_CONFIG } from '@/modules/wallet/bridge/bridge-config';

describe('bridge-config', () => {
  it('should expose the proxy configuration constants', () => {
    expect(PROXY_CONFIG).toStrictEqual({
      BRIDGE_PAGE_DELAY: 250,
      CONNECTION_TIMEOUT: 30000,
      HEALTH_CHECK_INTERVAL: 5000,
      RETRY_INTERVAL: 500,
      SERVER_TIMEOUT: 30000,
    });
  });

  it('should expose the websocket client configuration constants', () => {
    expect(CLIENT_CONFIG).toStrictEqual({
      DEFAULT_BASE_PORT: 40011,
      MAX_RETRIES: 5,
      RETRY_DELAY: 500,
    });
  });
});
