import { readFile } from 'node:fs/promises';
import * as path from 'node:path';
import { URL } from 'node:url';
import { sanitizePath } from '@electron/main/path-sanitizer';
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
const INDEX_HTML = 'index.html';

export function getMimeType(pathName: string): string {
  const extension = path.extname(pathName).toLowerCase();
  return MIME_TYPES_BY_EXTENSION[extension] ?? 'application/octet-stream';
}

/**
 * Resolves a request path to a file inside `baseDir`, guarding against path
 * traversal. Returns the absolute file path, or `undefined` if the request
 * escapes the served directory.
 */
function resolveFilePath(baseDir: string, requestFile: string): string | undefined {
  const filePath = path.resolve(path.join(baseDir, requestFile));
  const resolvedBaseDir = path.resolve(baseDir);
  if (filePath !== resolvedBaseDir && !filePath.startsWith(resolvedBaseDir + path.sep))
    return undefined;

  return filePath;
}

/**
 * Whether a sanitized request path asks for the entry document rather than a file.
 *
 * @remarks
 * The renderer loads `app://localhost/index.html`, but a reload or an in-app navigation can
 * request the bare origin or a hash route instead. Neither names a file, so both would resolve
 * to the served directory itself and fail to read. `sanitizePath` has already stripped the
 * leading slash by this point, so the bare origin arrives as an empty string and a hash route
 * as `#/...`, not `/` and `/#/...`.
 */
function isEntryDocumentRequest(requestFile: string): boolean {
  return !requestFile || requestFile.startsWith('#/');
}

async function fileResponse(filePath: string): Promise<Response> {
  const data = await readFile(filePath);
  return new Response(new Uint8Array(data), {
    status: 200,
    headers: {
      'Content-Type': getMimeType(filePath),
    },
  });
}

export function createProtocol(
  scheme: string,
  customProtocol?: Protocol,
  baseDir: string = currentDir,
): void {
  const protocolToUse = customProtocol ?? protocol;

  protocolToUse.handle(scheme, async (request) => {
    try {
      const url = new URL(request.url);
      const pathname = decodeURIComponent(url.pathname);
      let requestFile = sanitizePath(pathname);

      if (isEntryDocumentRequest(requestFile))
        requestFile = INDEX_HTML;

      const filePath = resolveFilePath(baseDir, requestFile);
      if (!filePath) {
        return new Response('Forbidden', {
          status: 403,
          headers: { 'Content-Type': 'text/plain' },
        });
      }

      try {
        return await fileResponse(filePath);
      }
      catch {
        // No extension means a client route rather than an asset; a missing asset gets its 404.
        if (path.extname(requestFile) === '') {
          const indexPath = resolveFilePath(baseDir, INDEX_HTML);
          if (indexPath) {
            try {
              return await fileResponse(indexPath);
            }
            catch { /* fall through to 404 */ }
          }
        }

        console.warn(`File not found via ${scheme}:// protocol: ${requestFile}`);
        return new Response('File not found', {
          status: 404,
          headers: { 'Content-Type': 'text/plain' },
        });
      }
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
