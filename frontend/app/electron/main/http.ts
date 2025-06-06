import type { LogService } from '@electron/main/log-service';
import type { Buffer } from 'node:buffer';
import fs from 'node:fs';
import http, { type IncomingMessage, type OutgoingHttpHeaders, type Server, type ServerResponse } from 'node:http';
import path from 'node:path';
import { getMimeType } from '@electron/main/create-protocol';
import { assert } from '@rotki/common';
import { checkIfDevelopment } from '@shared/utils';
import * as httpProxy from 'http-proxy';

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
  REQUEST_SIZE_LIMIT: 'Only requests up to 0.5MB are allowed',
  INVALID_CONTENT_LENGTH: 'No valid content length',
  RESOURCE_NOT_FOUND: 'Resource not found',
} as const;

type HttpErrorMessage = typeof HttpErrorMessage[keyof typeof HttpErrorMessage];

type Callback = (addresses: string[]) => void;

export class HttpServer {
  private static readonly applicationJson = 'application/json';
  private static readonly headersHtml = { 'Content-Type': 'text/html' };
  private static readonly headerJson = { 'Content-Type': HttpServer.applicationJson };
  private static readonly maxContentLength = 524288;

  private static readonly fileWhitelist = [
    'address-import/img/alert.svg',
    'address-import/img/done.svg',
    'address-import/img/rotki.svg',
    'address-import/js/vue.global.prod.js',
    'apple-touch-icon.png',
  ];

  private server: Server | undefined;

  constructor(private readonly logger: LogService) {}

  private error(message: HttpErrorMessage) {
    return JSON.stringify({
      message,
    });
  }

  private invalidRequest(res: ServerResponse, message: HttpErrorMessage, status: HttpStatus = HttpStatus.BAD_REQUEST) {
    res.writeHead(status, HttpServer.headerJson);
    res.write(this.error(message));
    res.end();
  }

  private okResponse(res: ServerResponse, body: Buffer | string, headers?: OutgoingHttpHeaders) {
    res.writeHead(HttpStatus.OK, headers);
    res.write(body);
    res.end();
  }

  private handleAddresses(req: IncomingMessage, res: ServerResponse, cb: Callback) {
    if (req.headers['content-type'] !== HttpServer.applicationJson) {
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

  private serveFile(res: ServerResponse, paths: string, url: string) {
    const requestedPath = this.sanitize(url);
    if (!HttpServer.fileWhitelist.includes(requestedPath)) {
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

    this.okResponse(res, fs.readFileSync(filePath), contentType ? { 'Content-Type': contentType } : undefined);
  }

  private sanitize(requestedPath: string): string {
    return requestedPath
      .replace(/\.{2,}/g, '')
      .replace(/\\{2,}|\/{2,}/g, '')
      .replace(/^\\|^\//g, '')
      .replace('~', '');
  }

  private isAllowed(basePath: string, servePath: string): boolean {
    const requestedPath = this.sanitize(servePath);
    if (!HttpServer.fileWhitelist.includes(requestedPath))
      return false;

    const filePath = path.join(basePath, requestedPath);
    return fs.existsSync(filePath);
  }

  private handleRequests(req: IncomingMessage, res: ServerResponse, cb: Callback) {
    const contentLengthHeader = req.headers['content-length'];
    if (contentLengthHeader) {
      try {
        const contentLength = Number.parseInt(contentLengthHeader);
        if (contentLength > HttpServer.maxContentLength) {
          this.invalidRequest(res, HttpErrorMessage.REQUEST_SIZE_LIMIT, HttpStatus.BAD_REQUEST);
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
      this.okResponse(res, fs.readFileSync(path.join(basePath, 'address-import/import.html')), HttpServer.headersHtml);
    }
    else if (url === '/import' && req.method === 'POST') {
      this.handleAddresses(req, res, cb);
      this.stop();
    }
    else if (this.isAllowed(basePath, url)) {
      this.serveFile(res, basePath, url);
    }
    else {
      this.invalidRequest(res, HttpErrorMessage.RESOURCE_NOT_FOUND, HttpStatus.NOT_FOUND);
    }
  }

  public start(cb: Callback, port = 43432): number {
    if (!(this.server?.listening)) {
      this.logger.log(`Address Import Server: Listening at: http://localhost:${port}`);
      this.server = http.createServer((req, resp) => this.handleRequests(req, resp, cb));
      this.server.listen(port);
    }

    const address = this.server.address();
    assert(address && typeof address !== 'string');
    return address.port;
  }

  public stop() {
    this.logger.log('Address Import Server: Stopped');
    if (this.server?.listening)
      this.server.close();
  }

  public startWalletConnectBridgeServer(port: number) {
    const devServerUrl = import.meta.env.VITE_DEV_SERVER_URL;
    const isDev = !!devServerUrl;

    if (isDev) {
      // @ts-expect-error  Property createProxyServer does not exist on type typeof Server
      const proxy = httpProxy.createProxyServer({
        target: devServerUrl,
        changeOrigin: true,
      });

      const server = http.createServer((req, res) => {
        if (req && req.url && (req.url === '/' || req.url.startsWith('/#/'))) {
          req.url = '/#/wallet-bridge'; // Ensure main app loads wallet-bridge
        }

        // Proxy request to Vite server
        proxy.web(req, res, {}, (err: any) => {
          this.logger.log(`Proxy error: ${err}`);
          res.writeHead(HttpStatus.INTERNAL_SERVER_ERROR, { 'Content-Type': 'text/plain' });
          res.end('Proxy error');
        });
      });

      server.listen(port, () => {
        this.logger.log(`Dev Proxy Server started at http://localhost:${port}`);
      });
    }
    else {
      const currentDir = import.meta.dirname;

      const server = http.createServer((req, res) => {
        const url = new URL(`http://localhost:${port}${req.url}`);
        const pathname = decodeURIComponent(url.pathname);

        let requestFile = path.normalize(pathname)
          .replace(/^(\.\.[/\\])+/, '') // Remove leading "../" sequences
          .replace(/^[/\\]+/, '') // Remove leading slashes
          .replace(/~/g, ''); // Remove tilde characters

        if (!requestFile || requestFile === '/' || requestFile.startsWith('/#/')) {
          requestFile = 'index.html'; // Always load index.html if on root or SPA route
        }

        const filePath = path.join(currentDir, requestFile);

        if (!filePath.startsWith(currentDir)) {
          res.writeHead(HttpStatus.FORBIDDEN, { 'Content-Type': 'text/plain' });
          return res.end('403 Forbidden: Access Denied');
        }

        if (!fs.existsSync(filePath)) {
          res.writeHead(HttpStatus.NOT_FOUND, { 'Content-Type': 'text/plain' });
          res.end(`404 File not Found`);
          return;
        }

        fs.readFile(filePath, (err, data) => {
          if (err) {
            res.writeHead(HttpStatus.INTERNAL_SERVER_ERROR, { 'Content-Type': 'text/plain' });
            res.end(`500 Internal Server Error: Failed to load ${filePath}\nError: ${err.message}`);
          }
          else {
            res.writeHead(HttpStatus.OK, { 'Content-Type': getMimeType(filePath) });
            res.end(data);
          }
        });
      });

      server.listen(port, () => {
        this.logger.log(`Wallet bridge server started at http://localhost:${port}`);
      });
    }
  }
}
