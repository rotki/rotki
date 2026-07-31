// @vitest-environment node
import net from 'node:net';
import { describe, expect, it } from 'vitest';
import { selectPort } from './port-utils';

/** Hold a port for the duration of one case, then give it back. */
async function occupy(port: number, host: string): Promise<net.Server> {
  const server = net.createServer();
  await new Promise<void>((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, host, resolve);
  });
  return server;
}

async function release(server: net.Server): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    server.close(error => error ? reject(error) : resolve());
  });
}

async function freePort(host: string): Promise<number> {
  const server = await occupy(0, host);
  const address = server.address();
  if (!address || typeof address === 'string')
    throw new Error('the probe server reported no port');
  await release(server);
  return address.port;
}

describe('selectPort', () => {
  it('should probe the exact IPv4 address used by the service', async () => {
    const server = await occupy(0, '127.0.0.1');

    try {
      const address = server.address();
      expect(address).not.toBeNull();
      expect(typeof address).not.toBe('string');
      if (!address || typeof address === 'string')
        return;

      expect(await selectPort(address.port, '127.0.0.1')).toBeGreaterThan(address.port);
    }
    finally {
      await release(server);
    }
  });

  it('should return the start port when nothing holds it', async () => {
    const port = await freePort('127.0.0.1');

    expect(await selectPort(port, '127.0.0.1')).toBe(port);
  });

  it('should walk up past every port already taken', async () => {
    // Two concurrent dev runs rely on this: the second walks past the first
    // rather than reserving a slot anywhere.
    const first = await freePort('127.0.0.1');
    const held = [await occupy(first, '127.0.0.1'), await occupy(first + 1, '127.0.0.1')];

    try {
      expect(await selectPort(first, '127.0.0.1')).toBeGreaterThan(first + 1);
    }
    finally {
      await Promise.all(held.map(release));
    }
  });

  it('should report the port it actually bound, not the one asked for', async () => {
    // `0` means "any free port": the walk must report what the OS handed back,
    // since that is the port the caller has to pass to the service.
    const port = await selectPort(0, '127.0.0.1');

    expect(port).toBeGreaterThan(0);
  });

  it('should surface a failure that is not the port being unavailable', async () => {
    // A host this machine cannot bind fails with EADDRNOTAVAIL/EINVAL, neither
    // of which is a busy port — walking 60,000 times would just hide it.
    await expect(selectPort(4242, '203.0.113.1')).rejects.toThrow();
  });
});
