import type { Buffer } from 'node:buffer';
import fs from 'node:fs';
import http, { type IncomingMessage, type OutgoingHttpHeaders, type Server, type ServerResponse } from 'node:http';
import path from 'node:path';
import { assert } from '@rotki/common';
import { checkIfDevelopment } from '@shared/utils';

type Callback = (addresses: string[]) => void;

const applicationJson = 'application/json';
const headersHtml = { 'Content-Type': 'text/html' };
const headerJson = { 'Content-Type': applicationJson };

const STATUS_OK = 200;
const STATUS_BAD_REQUEST = 400;
const STATUS_NOT_FOUND = 404;
const STATUS_CONTENT_LENGTH_REQUIRED = 411;

const FILE_WHITELIST = [
  'address-import/img/alert.svg',
  'address-import/img/done.svg',
  'address-import/img/rotki.svg',
  'address-import/js/vue.global.prod.js',
  'apple-touch-icon.png',
];

let server: Server;

function error(message: string) {
  return JSON.stringify({
    message,
  });
}

function invalidRequest(res: ServerResponse, message: string, status: number = STATUS_BAD_REQUEST) {
  res.writeHead(status, headerJson);
  res.write(error(message));
  res.end();
}

function okResponse(res: ServerResponse, body: Buffer | string, headers?: OutgoingHttpHeaders) {
  res.writeHead(STATUS_OK, headers);
  res.write(body);
  res.end();
}

function handleAddresses(req: IncomingMessage, res: ServerResponse, cb: Callback) {
  if (req.headers['content-type'] !== applicationJson) {
    invalidRequest(res, `Invalid content type: ${req.headers['content-type']}`);
    return;
  }
  let data = '';
  req.on('data', (chunk) => {
    data += chunk;
  });
  req.on('end', () => {
    try {
      const payload = JSON.parse(data);
      if (!('addresses' in payload) || !Array.isArray(payload.addresses)) {
        invalidRequest(res, 'Invalid request schema');
        return;
      }
      cb(payload.addresses);
      res.writeHead(STATUS_OK);
      res.end();
    }
    catch {
      invalidRequest(res, 'Malformed JSON');
    }
  });
}

function serveFile(res: ServerResponse, paths: string, url: string) {
  const requestedPath = sanitize(url);
  if (!FILE_WHITELIST.includes(requestedPath)) {
    invalidRequest(res, 'non whitelisted path accessed');
    return;
  }
  const filePath = path.join(paths, requestedPath);
  const extension = path.extname(filePath);
  let contentType = null;
  if (extension.includes('svg'))
    contentType = 'image/svg+xml';
  else if (extension.includes('ico'))
    contentType = 'image/vnd.microsoft.icon';

  okResponse(res, fs.readFileSync(filePath), contentType ? { 'Content-Type': contentType } : undefined);
}

function sanitize(requestedPath: string): string {
  return requestedPath
    .replace(/\.{2,}/g, '')
    .replace(/\\{2,}|\/{2,}/g, '')
    .replace(/^\\|^\//g, '')
    .replace('~', '');
}

function isAllowed(basePath: string, servePath: string): boolean {
  const requestedPath = sanitize(servePath);
  if (!FILE_WHITELIST.includes(requestedPath))
    return false;

  const filePath = path.join(basePath, requestedPath);
  return fs.existsSync(filePath);
}

function handleRequests(req: IncomingMessage, res: ServerResponse, cb: Callback) {
  const contentLengthHeader = req.headers['content-length'];
  if (contentLengthHeader) {
    try {
      const contentLength = Number.parseInt(contentLengthHeader);
      if (contentLength > 524288) {
        invalidRequest(res, 'Only requests up to 0.5MB are allowed', STATUS_BAD_REQUEST);
        return;
      }
    }
    catch {
      invalidRequest(res, 'No valid content length', STATUS_CONTENT_LENGTH_REQUIRED);
      return;
    }
  }
  const dirname = import.meta.dirname;
  const basePath = checkIfDevelopment() ? path.join(dirname, '..', 'public') : dirname;
  const url = req.url ?? '';
  if (url === '/') {
    okResponse(res, fs.readFileSync(path.join(basePath, 'address-import/import.html')), headersHtml);
  }
  else if (url === '/import' && req.method === 'POST') {
    handleAddresses(req, res, cb);
    stopHttp();
  }
  else if (isAllowed(basePath, url)) {
    serveFile(res, basePath, url);
  }
  else {
    invalidRequest(res, `${req.url} was not found on server`, STATUS_NOT_FOUND);
  }
}

export function startHttp(cb: Callback, port = 43432): number {
  if (!(server?.listening)) {
    // eslint-disable-next-line no-console
    console.log(`Address Import Server: Listening at: http://localhost:${port}`);
    server = http.createServer((req, resp) => handleRequests(req, resp, cb));
    server.listen(port);
  }

  const address = server.address();
  assert(address && typeof address !== 'string');
  return address.port;
}

export function stopHttp() {
  // eslint-disable-next-line no-console
  console.log('Address Import Server: Stopped');
  if (server?.listening)
    server.close();
}
