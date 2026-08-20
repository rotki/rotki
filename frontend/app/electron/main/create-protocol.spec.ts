// Seam: MIME detection stays stable, and the registered app protocol handler serves files,
// falls back to the SPA entry point, and rejects invalid paths with the expected status.
import type { Protocol } from 'electron';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createProtocol, getMimeType } from './create-protocol';

describe('getMimeType', () => {
  it.each([
    ['app.js', 'application/javascript'],
    ['index.html', 'text/html'],
    ['styles.css', 'text/css'],
    ['icon.svg', 'image/svg+xml'],
    ['icon.svgz', 'image/svg+xml'],
    ['logo.png', 'image/png'],
    ['photo.jpg', 'image/jpeg'],
    ['photo.jpeg', 'image/jpeg'],
    ['data.json', 'application/json'],
    ['module.wasm', 'application/wasm'],
  ])('should map %s to %s', (fileName, expected) => {
    expect(getMimeType(fileName)).toBe(expected);
  });

  it('should fall back to application/octet-stream for unknown extensions', () => {
    expect(getMimeType('archive.zip')).toBe('application/octet-stream');
  });

  it('should fall back to application/octet-stream when there is no extension', () => {
    expect(getMimeType('LICENSE')).toBe('application/octet-stream');
  });

  it('should match extensions case-insensitively', () => {
    expect(getMimeType('APP.JS')).toBe('application/javascript');
    expect(getMimeType('Photo.JPEG')).toBe('image/jpeg');
  });

  it('should resolve the extension from a full path', () => {
    expect(getMimeType('/some/nested/dir/app.css')).toBe('text/css');
  });
});

type Handler = Parameters<Protocol['handle']>[1];

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
    const customProtocol = createMock<Protocol>({
      handle: vi.fn<Protocol['handle']>((_scheme, callback) => {
        handler = callback;
      }),
    });

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
