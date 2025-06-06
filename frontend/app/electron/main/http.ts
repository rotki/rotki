import type { LogService } from '@electron/main/log-service';
import type { Buffer } from 'node:buffer';
import fs from 'node:fs';
import http, { type IncomingMessage, type OutgoingHttpHeaders, type Server, type ServerResponse } from 'node:http';
import path from 'node:path';
import process from 'node:process';
import { getMimeType } from '@electron/main/create-protocol';
import { assert } from '@rotki/common';
import { checkIfDevelopment } from '@shared/utils';
import * as httpProxy from 'http-proxy';

export const HttpStatus = {
  OK: 200,
  BAD_REQUEST: 400,
  NOT_FOUND: 404,
  CONTENT_LENGTH_REQUIRED: 411,
} as const;

type Callback = (addresses: string[]) => void;

export class HttpServer {
  private static readonly applicationJson = 'application/json';
  private static readonly headersHtml = { 'Content-Type': 'text/html' };
  private static readonly headerJson = { 'Content-Type': HttpServer.applicationJson };

  private static readonly fileWhitelist = [
    'address-import/img/alert.svg',
    'address-import/img/done.svg',
    'address-import/img/rotki.svg',
    'address-import/js/vue.global.prod.js',
    'apple-touch-icon.png',
  ];

  private server: Server | undefined;

  constructor(private readonly logger: LogService) {}

  private error(message: string) {
    return JSON.stringify({
      message,
    });
  }

  private invalidRequest(res: ServerResponse, message: string, status: number = HttpStatus.BAD_REQUEST) {
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
      this.invalidRequest(res, `Invalid content type: ${req.headers['content-type']}`);
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
          this.invalidRequest(res, 'Invalid request schema');
          return;
        }
        cb(payload.addresses);
        res.writeHead(HttpStatus.OK);
        res.end();
      }
      catch {
        this.invalidRequest(res, 'Malformed JSON');
      }
    });
  }

  private serveFile(res: ServerResponse, paths: string, url: string) {
    const requestedPath = this.sanitize(url);
    if (!HttpServer.fileWhitelist.includes(requestedPath)) {
      this.invalidRequest(res, 'non whitelisted path accessed');
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
        if (contentLength > 524288) {
          this.invalidRequest(res, 'Only requests up to 0.5MB are allowed', HttpStatus.BAD_REQUEST);
          return;
        }
      }
      catch {
        this.invalidRequest(res, 'No valid content length', HttpStatus.CONTENT_LENGTH_REQUIRED);
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
      this.invalidRequest(res, `${req.url} was not found on server`, HttpStatus.NOT_FOUND);
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
          console.error('Proxy error:', err);
          res.writeHead(500, { 'Content-Type': 'text/plain' });
          res.end('Proxy error');
        });
      });

      server.listen(port, () => {
        this.logger.log(`Dev Proxy Server started at http://localhost:${port}`);
      });
    }
    else {
      const resourcesDir = process.resourcesPath ? process.resourcesPath : import.meta.dirname;
      const distPath = path.join(resourcesDir, 'app.asar', 'dist');
      const indexPath = path.join(distPath, 'index.html');

      const server = http.createServer((req, res) => {
        let requestFile = req.url?.split('?')[0] ?? '/';

        requestFile = path.normalize(requestFile).replace(/^(\.\.[/\\])+/, '');

        if (requestFile === '/' || requestFile.startsWith('/#/')) {
          requestFile = '/index.html'; // Always load index.html if on root or SPA route
        }

        const filePath = path.join(distPath, requestFile);

        if (!filePath.startsWith(distPath)) {
          res.writeHead(403, { 'Content-Type': 'text/plain' });
          return res.end('403 Forbidden: Access Denied');
        }

        const mimeType = getMimeType(filePath);

        fs.readFile(fs.existsSync(filePath) ? filePath : indexPath, (err, data) => {
          if (err) {
            res.writeHead(500, { 'Content-Type': 'text/plain' });
            res.end(`500 Internal Server Error: Failed to load ${filePath}\nError: ${err.message}`);
          }
          else {
            res.writeHead(200, { 'Content-Type': mimeType });
            res.end(data);
          }
        });
      });

      server.listen(port, () => {
        this.logger.log(`Static Server started at http://localhost:${port}`);
      });
    }
  }
}
