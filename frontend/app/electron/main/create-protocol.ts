import { readFile } from 'node:fs';
import * as path from 'node:path';
import { URL } from 'node:url';
import { type Protocol, protocol } from 'electron';

const currentDir = import.meta.dirname;

export function getMimeType(pathName: string): string {
  const extension = path.extname(pathName).toLowerCase();

  if (extension === '.js')
    return 'text/javascript';
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

  return '';
}

export function createProtocol(scheme: string, customProtocol?: Protocol) {
  (customProtocol || protocol).registerBufferProtocol(scheme, (request, respond) => {
    let pathName = new URL(request.url).pathname;
    pathName = decodeURI(pathName); // Needed in case URL contains spaces

    readFile(path.join(currentDir, pathName), (error, data) => {
      if (error)
        console.error(`Failed to read ${pathName} on ${scheme} protocol`, error);

      const mimeType = getMimeType(pathName);
      respond({ mimeType, data });
    });
  });
}
