import type { LogService } from '@electron/main/log-service';
import type { Buffer } from 'node:buffer';
import fs from 'node:fs/promises';
import http, { type IncomingMessage, type OutgoingHttpHeaders, type Server, type ServerResponse } from 'node:http';
import path from 'node:path';
import { sanitizePath } from '@electron/main/path-sanitizer';
import { assert } from '@rotki/common';
import { checkIfDevelopment } from '@shared/utils';

const HttpStatus = {
  OK: 200,
  BAD_REQUEST: 400,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONTENT_LENGTH_REQUIRED: 411,
  INTERNAL_SERVER_ERROR: 500,
} as const;

type HttpStatus = typeof HttpStatus[keyof typeof HttpStatus];

const HttpErrorMessage = {
  INVALID_CONTENT_TYPE: 'Invalid content type',
  INVALID_REQUEST_SCHEMA: 'Invalid request schema',
  MALFORMED_JSON: 'Malformed JSON',
  ACCESS_DENIED: 'Access denied',
  INVALID_CONTENT_LENGTH: 'No valid content length',
  RESOURCE_NOT_FOUND: 'Resource not found',
} as const;

type HttpErrorMessage = typeof HttpErrorMessage[keyof typeof HttpErrorMessage];

type AddressImportCallback = (addresses: string[]) => void;

export class AddressImportServer {
  private static readonly applicationJson = 'application/json';
  private static readonly headersHtml = { 'Content-Type': 'text/html' };
  private static readonly headerJson = { 'Content-Type': AddressImportServer.applicationJson };
  private static readonly defaultMaxContentLength = 524288; // 0.5MB

  private readonly maxContentLength: number;

  private static readonly fileWhitelist = [
    'address-import/img/alert.svg',
    'address-import/img/done.svg',
    'address-import/img/rotki.svg',
    'address-import/js/vue.global.prod.js',
    'apple-touch-icon.png',
  ];

  private server: Server | undefined;

  constructor(private readonly logger: LogService, maxContentLength?: number) {
    this.maxContentLength = maxContentLength ?? AddressImportServer.defaultMaxContentLength;
  }

  private error(message: HttpErrorMessage | string) {
    return JSON.stringify({
      message,
    });
  }

  private invalidRequest(res: ServerResponse, message: HttpErrorMessage | string, status: HttpStatus = HttpStatus.BAD_REQUEST) {
    res.writeHead(status, AddressImportServer.headerJson);
    res.write(this.error(message));
    res.end();
  }

  private okResponse(res: ServerResponse, body: Buffer | string, headers?: OutgoingHttpHeaders) {
    res.writeHead(HttpStatus.OK, headers);
    res.write(body);
    res.end();
  }

  private handleAddresses(req: IncomingMessage, res: ServerResponse, cb: AddressImportCallback) {
    if (req.headers['content-type'] !== AddressImportServer.applicationJson) {
      this.invalidRequest(res, HttpErrorMessage.INVALID_CONTENT_TYPE);
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
          this.invalidRequest(res, HttpErrorMessage.INVALID_REQUEST_SCHEMA);
          return;
        }
        cb(payload.addresses);
        res.writeHead(HttpStatus.OK);
        res.end();
      }
      catch {
        this.invalidRequest(res, HttpErrorMessage.MALFORMED_JSON);
      }
    });
  }

  private async serveFile(res: ServerResponse, paths: string, url: string): Promise<void> {
    const requestedPath = sanitizePath(url);
    if (!AddressImportServer.fileWhitelist.includes(requestedPath)) {
      this.logger.warn(`Access denied for non-whitelisted path: ${requestedPath}`);
      this.invalidRequest(res, HttpErrorMessage.ACCESS_DENIED, HttpStatus.FORBIDDEN);
      return;
    }

    const filePath = path.join(paths, requestedPath);
    const extension = path.extname(filePath);
    let contentType = null;
    if (extension.includes('svg'))
      contentType = 'image/svg+xml';
    else if (extension.includes('ico'))
      contentType = 'image/vnd.microsoft.icon';

    try {
      const fileData = await fs.readFile(filePath);
      this.okResponse(res, fileData, contentType ? { 'Content-Type': contentType } : undefined);
    }
    catch (error) {
      this.logger.error(`Failed to read file ${filePath}:`, error);
      this.invalidRequest(res, HttpErrorMessage.RESOURCE_NOT_FOUND, HttpStatus.NOT_FOUND);
    }
  }

  private async isAllowed(basePath: string, servePath: string): Promise<boolean> {
    const requestedPath = sanitizePath(servePath);
    if (!AddressImportServer.fileWhitelist.includes(requestedPath))
      return false;

    const filePath = path.join(basePath, requestedPath);
    const resolvedBasePath = path.resolve(basePath);
    const resolvedFilePath = path.resolve(filePath);

    // Security check: ensure the resolved path is within the base directory
    if (!resolvedFilePath.startsWith(resolvedBasePath)) {
      this.logger.warn(`Path traversal attempt detected: ${requestedPath} -> ${resolvedFilePath}`);
      return false;
    }

    try {
      await fs.access(resolvedFilePath);
      return true;
    }
    catch {
      return false;
    }
  }

  private async handleRequests(req: IncomingMessage, res: ServerResponse, cb: AddressImportCallback): Promise<void> {
    try {
      const contentLengthHeader = req.headers['content-length'];
      if (contentLengthHeader) {
        try {
          const contentLength = Number.parseInt(contentLengthHeader);
          if (contentLength > this.maxContentLength) {
            const limitMB = (this.maxContentLength / 1024 / 1024).toFixed(1);
            this.invalidRequest(res, `Only requests up to ${limitMB}MB are allowed`, HttpStatus.BAD_REQUEST);
            return;
          }
        }
        catch {
          this.invalidRequest(res, HttpErrorMessage.INVALID_CONTENT_LENGTH, HttpStatus.CONTENT_LENGTH_REQUIRED);
          return;
        }
      }

      const dirname = import.meta.dirname;
      const basePath = checkIfDevelopment() ? path.join(dirname, '..', 'public') : dirname;
      const url = req.url ?? '';

      if (url === '/') {
        try {
          const htmlContent = await fs.readFile(path.join(basePath, 'address-import/import.html'));
          this.okResponse(res, htmlContent, AddressImportServer.headersHtml);
        }
        catch (error) {
          this.logger.error('Failed to read import.html:', error);
          this.invalidRequest(res, HttpErrorMessage.RESOURCE_NOT_FOUND, HttpStatus.NOT_FOUND);
        }
      }
      else if (url === '/import' && req.method === 'POST') {
        this.handleAddresses(req, res, cb);
        this.stop();
      }
      else if (await this.isAllowed(basePath, url)) {
        await this.serveFile(res, basePath, url);
      }
      else {
        this.invalidRequest(res, HttpErrorMessage.RESOURCE_NOT_FOUND, HttpStatus.NOT_FOUND);
      }
    }
    catch (error) {
      this.logger.error('Error handling request:', error);
      this.invalidRequest(res, HttpErrorMessage.RESOURCE_NOT_FOUND, HttpStatus.INTERNAL_SERVER_ERROR);
    }
  }

  public start(cb: AddressImportCallback, port = 43432): number {
    if (!(this.server?.listening)) {
      this.logger.info(`Address Import Server: Listening at: http://localhost:${port}`);
      this.server = http.createServer((req, resp) => {
        this.handleRequests(req, resp, cb).catch((error) => {
          this.logger.error('Unhandled error in request handler:', error);
        });
      });
      this.server.listen(port);
    }

    const address = this.server.address();
    assert(address && typeof address !== 'string');
    return address.port;
  }

  public stop() {
    this.logger.info('Address Import Server: Stopped');
    if (this.server?.listening)
      this.server.close();
  }

  public isListening(): boolean {
    return this.server?.listening ?? false;
  }
}
