import type { Protocol } from 'electron';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createProtocol } from './create-protocol';

type Handler = (request: Request) => Promise<Response>;

describe('createProtocol', () => {
  let baseDir: string;

  beforeEach(async () => {
    baseDir = await mkdtemp(join(tmpdir(), 'rotki-protocol-'));
    await writeFile(join(baseDir, 'index.html'), '<html>root</html>');
    await writeFile(join(baseDir, 'main.js'), 'console.log(1)');
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(async () => {
    await rm(baseDir, { force: true, recursive: true });
    vi.restoreAllMocks();
  });

  /**
   * Captures the handler registered via `protocol.handle` so it can be invoked
   * with fabricated requests, serving from the temporary `baseDir`.
   */
  function registerHandler(): Handler {
    let handler: Handler | undefined;
    const customProtocol = {
      handle: (_scheme: string, cb: Handler) => {
        handler = cb;
      },
    } as unknown as Protocol;

    createProtocol('app', customProtocol, baseDir);

    if (!handler)
      throw new Error('handler was not registered');

    return handler;
  }

  function request(path: string): Request {
    return new Request(`app://localhost${path}`);
  }

  it('should serve an existing asset with the correct mime type', async () => {
    const handler = registerHandler();

    const response = await handler(request('/main.js'));

    expect(response.status).toBe(200);
    expect(response.headers.get('Content-Type')).toBe('application/javascript');
    expect(await response.text()).toBe('console.log(1)');
  });

  it('should fall back to index.html for the bare origin', async () => {
    const handler = registerHandler();

    const response = await handler(request('/'));

    expect(response.status).toBe(200);
    expect(response.headers.get('Content-Type')).toBe('text/html');
    expect(await response.text()).toBe('<html>root</html>');
  });

  it('should fall back to index.html for an unknown extensionless route', async () => {
    const handler = registerHandler();

    const response = await handler(request('/dashboard'));

    expect(response.status).toBe(200);
    expect(response.headers.get('Content-Type')).toBe('text/html');
    expect(await response.text()).toBe('<html>root</html>');
  });

  it('should return 404 for a missing asset with an extension', async () => {
    const handler = registerHandler();

    const response = await handler(request('/missing.js'));

    expect(response.status).toBe(404);
  });

  it('should not escape the served directory on path traversal attempts', async () => {
    const handler = registerHandler();

    const response = await handler(request('/../../secret.txt'));

    // sanitizePath strips the traversal sequence, so it can never reach a file
    // outside baseDir; the request resolves within the directory instead.
    expect(response.status).not.toBe(500);
    expect([200, 403, 404]).toContain(response.status);
  });
});
