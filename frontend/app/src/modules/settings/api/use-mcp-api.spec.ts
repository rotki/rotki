import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { useMcpApi } from './use-mcp-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/settings/mcp-api', () => {
  it('should generate and deserialize an MCP bearer token', async () => {
    server.use(
      http.post(`${backendUrl}/api/1/mcp/token`, () =>
        HttpResponse.json({
          result: {
            access_token: 'signed-token',
            expires_at: 1_800_000_000,
            token_type: 'Bearer',
          },
          message: '',
        })),
    );

    const { generateMcpToken } = useMcpApi();

    await expect(generateMcpToken()).resolves.toEqual({
      accessToken: 'signed-token',
      expiresAt: 1_800_000_000,
      tokenType: 'Bearer',
    });
  });
});
