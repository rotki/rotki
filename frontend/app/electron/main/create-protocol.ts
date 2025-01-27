import { readFile } from 'node:fs/promises';
import * as path from 'node:path';
import { URL } from 'node:url';
import { type Protocol, protocol } from 'electron';

const currentDir = import.meta.dirname;

export function getMimeType(pathName: string): string {
  const extension = path.extname(pathName).toLowerCase();

  if (extension === '.js')
    return 'application/javascript';
  else if (extension === '.html')
    return 'text/html';
  else if (extension === '.css')
    return 'text/css';
  else if (extension === '.svg' || extension === '.svgz')
    return 'image/svg+xml';
  else if (extension === '.png')
    return 'image/png';
  else if (extension === '.jpg' || extension === '.jpeg')
    return 'image/jpeg';
  else if (extension === '.json')
    return 'application/json';
  else if (extension === '.wasm')
    return 'application/wasm';

  return 'application/octet-stream';
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

      return new Response(data, {
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
