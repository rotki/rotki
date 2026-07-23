import { readFile } from 'node:fs/promises';
import * as path from 'node:path';
import { URL } from 'node:url';
import { type Protocol, protocol } from 'electron';

const currentDir = import.meta.dirname;

const MIME_TYPES_BY_EXTENSION: Record<string, string> = {
  '.js': 'application/javascript',
  '.html': 'text/html',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.svgz': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.json': 'application/json',
  '.wasm': 'application/wasm',
};

export function getMimeType(pathName: string): string {
  const extension = path.extname(pathName).toLowerCase();
  return MIME_TYPES_BY_EXTENSION[extension] ?? 'application/octet-stream';
}

export function createProtocol(scheme: string, customProtocol?: Protocol) {
  const protocolToUse = customProtocol || protocol;

  protocolToUse.handle(scheme, async (request) => {
    try {
      const url = new URL(request.url);
      const pathname = decodeURIComponent(url.pathname);
      const filePath = path.join(currentDir, pathname);

      const data = await readFile(filePath);
      const mimeType = getMimeType(filePath);

      return new Response(new Uint8Array(data), {
        status: 200,
        headers: {
          'Content-Type': mimeType,
        },
      });
    }
    catch (error) {
      console.error(`Failed to load file via ${scheme}:// protocol`, error);

      return new Response(`Failed to load file`, {
        status: 500,
        headers: {
          'Content-Type': 'text/plain',
        },
      });
    }
  });
}
