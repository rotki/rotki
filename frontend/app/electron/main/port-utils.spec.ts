// @vitest-environment node
import net from 'node:net';
import { describe, expect, it } from 'vitest';
import { selectPort } from './port-utils';

describe('selectPort', () => {
  it('should probe the exact IPv4 address used by the service', async () => {
    const server = net.createServer();
    await new Promise<void>((resolve, reject) => {
      server.once('error', reject);
      server.listen(0, '127.0.0.1', resolve);
    });

    try {
      const address = server.address();
      expect(address).not.toBeNull();
      expect(typeof address).not.toBe('string');
      if (!address || typeof address === 'string')
        return;

      expect(await selectPort(address.port, '127.0.0.1')).toBeGreaterThan(address.port);
    }
    finally {
      await new Promise<void>((resolve, reject) => {
        server.close(error => error ? reject(error) : resolve());
      });
    }
  });
});
