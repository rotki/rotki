import type { LogService } from '@electron/main/log-service';
import fs from 'node:fs/promises';
import http, { type Server } from 'node:http';
import path from 'node:path';
import { getMimeType } from '@electron/main/create-protocol';
import { sanitizePath } from '@electron/main/path-sanitizer';
import httpProxy from 'http-proxy';

const HttpStatus = {
  OK: 200,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  INTERNAL_SERVER_ERROR: 500,
} as const;

export class AppServer {
  private server: Server | undefined;
  private readonly baseDirectory: string;

  constructor(private readonly logger: LogService, baseDirectory?: string) {
    this.baseDirectory = baseDirectory ?? import.meta.dirname;
  }

  public start(port: number, initialRoute?: string): void {
    const devServerUrl = import.meta.env.VITE_DEV_SERVER_URL;
    const isDev = !!devServerUrl;

    if (isDev) {
      this.startDevelopmentProxy(port, devServerUrl, initialRoute);
    }
    else {
      this.startProductionServer(port);
    }
  }

  private startDevelopmentProxy(port: number, devServerUrl: string, initialRoute?: string): void {
    const proxy = httpProxy.createProxyServer({
      target: devServerUrl,
      changeOrigin: true,
    });

    const server = http.createServer((req, res) => {
      // Log incoming requests for debugging
      this.logger.debug(`Proxy request: ${req.method} ${req.url}`);

      // Proxy all requests to Vite dev server
      proxy.web(req, res, {}, (err: Error | null) => {
        if (err) {
          this.logger.error('Proxy error:', err);
          res.writeHead(HttpStatus.INTERNAL_SERVER_ERROR, { 'Content-Type': 'text/plain' });
          res.end('Proxy error');
        }
      });
    });

    // Handle WebSocket upgrade requests (for HMR)
    server.on('upgrade', (req, socket, head) => {
      this.logger.debug(`WebSocket upgrade request: ${req.url}`);
      proxy.ws(req, socket, head, {}, (err: Error | null) => {
        if (err) {
          this.logger.error('WebSocket proxy error:', err);
          socket.destroy();
        }
      });
    });

    this.server = server;
    server.listen(port, () => {
      this.logger.info(`Development proxy server started at http://localhost:${port}`);
      if (initialRoute) {
        this.logger.info(`Initial route configured: ${initialRoute}`);
      }
    });

    server.on('error', (error) => {
      this.logger.error('Development proxy server error:', error);
    });
  }

  private startProductionServer(port: number): void {
    const server = http.createServer((req, res) => {
      this.handleProductionRequest(req, res, this.baseDirectory).catch((error) => {
        this.logger.error('Unhandled error in production request handler:', error);
        res.writeHead(HttpStatus.INTERNAL_SERVER_ERROR, { 'Content-Type': 'text/plain' });
        res.end('500 Internal Server Error');
      });
    });

    this.server = server;
    server.listen(port, () => {
      this.logger.info(`Production server started at http://localhost:${port}`);
    });

    server.on('error', (error) => {
      this.logger.error('Production server error:', error);
    });
  }

  private async handleProductionRequest(req: http.IncomingMessage, res: http.ServerResponse, currentDir: string): Promise<void> {
    try {
      const url = new URL(`http://localhost:${req.url}`);
      const pathname = decodeURIComponent(url.pathname);

      let requestFile = sanitizePath(pathname);

      // Serve index.html for SPA routes
      if (!requestFile || requestFile === '/' || requestFile.startsWith('/#/')) {
        requestFile = 'index.html';
      }

      const filePath = path.join(currentDir, requestFile);

      // Security check: ensure file is within the current directory
      const resolvedCurrentDir = path.resolve(currentDir);
      const resolvedFilePath = path.resolve(filePath);
      if (!resolvedFilePath.startsWith(resolvedCurrentDir)) {
        res.writeHead(HttpStatus.FORBIDDEN, { 'Content-Type': 'text/plain' });
        res.end('403 Forbidden: Access Denied');
        return;
      }

      try {
        // Check if file exists and read it
        const data = await fs.readFile(resolvedFilePath);
        res.writeHead(HttpStatus.OK, { 'Content-Type': getMimeType(resolvedFilePath) });
        res.end(data);
      }
      catch {
        // File doesn't exist or can't be read
        this.logger.warn(`File not found or unreadable: ${resolvedFilePath}`);
        res.writeHead(HttpStatus.NOT_FOUND, { 'Content-Type': 'text/plain' });
        res.end('404 File not Found');
      }
    }
    catch (error) {
      this.logger.error('Server error:', error);
      res.writeHead(HttpStatus.INTERNAL_SERVER_ERROR, { 'Content-Type': 'text/plain' });
      res.end('500 Internal Server Error');
    }
  }

  public isListening(): boolean {
    return this.server?.listening ?? false;
  }

  public stop(): void {
    this.logger.info('Stopping app server...');

    if (this.server?.listening) {
      this.server.close((err) => {
        if (err) {
          this.logger.error('Error closing app server:', err);
        }
        else {
          this.logger.info('App server closed');
        }
      });
      this.server = undefined;
    }
  }
}
