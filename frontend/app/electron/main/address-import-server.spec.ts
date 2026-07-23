// @vitest-environment node
import type { LogService } from '@electron/main/log-service';
import { createMock } from '@test/utils/create-mock';
import { afterEach, describe, expect, it, type Mock, vi } from 'vitest';
import { AddressImportServer } from './address-import-server';

describe('addressImportServer', () => {
  let server: AddressImportServer | undefined;

  afterEach(() => {
    server?.stop();
    server = undefined;
  });

  function startServer(cb: Mock = vi.fn(), maxContentLength?: number): string {
    server = new AddressImportServer(createMock<LogService>(), maxContentLength);
    const port = server.start(cb, 0);
    return `http://127.0.0.1:${port}`;
  }

  it('should reject a request whose content length exceeds the limit', async () => {
    const base = startServer(vi.fn(), 10);
    const res = await fetch(`${base}/import`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ addresses: ['0xabc', '0xdef', '0x123'] }),
    });
    expect(res.status).toBe(400);
    expect(await res.json()).toStrictEqual({ message: 'Only requests up to 0.0MB are allowed' });
  });

  it('should reject an import with a non-json content type', async () => {
    const base = startServer();
    const res = await fetch(`${base}/import`, {
      method: 'POST',
      headers: { 'content-type': 'text/plain' },
      body: '{}',
    });
    expect(res.status).toBe(400);
    expect(await res.json()).toStrictEqual({ message: 'Invalid content type' });
  });

  it('should invoke the callback with the parsed addresses', async () => {
    const cb = vi.fn();
    const base = startServer(cb);
    const res = await fetch(`${base}/import`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ addresses: ['0xabc', '0xdef'] }),
    });
    expect(res.status).toBe(200);
    expect(cb).toHaveBeenCalledWith(['0xabc', '0xdef']);
    expect(server?.isListening()).toBe(false);
  });

  it('should reject malformed json on import', async () => {
    const base = startServer();
    const res = await fetch(`${base}/import`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: '{ not valid json',
    });
    expect(res.status).toBe(400);
    expect(await res.json()).toStrictEqual({ message: 'Malformed JSON' });
  });

  it('should reject an import payload without an addresses array', async () => {
    const cb = vi.fn();
    const base = startServer(cb);
    const res = await fetch(`${base}/import`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ notAddresses: true }),
    });
    expect(res.status).toBe(400);
    expect(await res.json()).toStrictEqual({ message: 'Invalid request schema' });
    expect(cb).not.toHaveBeenCalled();
  });

  it('should return 404 for a non-whitelisted path', async () => {
    const base = startServer();
    const res = await fetch(`${base}/etc/passwd`);
    expect(res.status).toBe(404);
    expect(await res.json()).toStrictEqual({ message: 'Resource not found' });
  });
});
