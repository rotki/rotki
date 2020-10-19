import fs from 'fs';
import http, {
  IncomingMessage,
  OutgoingHttpHeaders,
  ServerResponse,
  Server
} from 'http';
import path from 'path';

type Callback = (addresses: string[]) => void;

const applicationJson = 'application/json';
const headersHtml = { 'Content-Type': 'text/html' };
const headerJson = { 'Content-Type': applicationJson };

const STATUS_OK = 200;
const STATUS_BAD_REQUEST = 400;
const STATUS_FORBIDDEN = 403;
const STATUS_NOT_FOUND = 404;
const STATUS_CONTENT_LENGTH_REQUIRED = 411;

let server: Server;

const error = (message: string) =>
  JSON.stringify({
    message
  });

function invalidRequest(
  req: IncomingMessage,
  res: ServerResponse,
  message: string,
  status: number = STATUS_BAD_REQUEST
) {
  res.writeHead(status, headerJson);
  res.write(error(message));
  res.end();
}

function okResponse(
  req: IncomingMessage,
  res: ServerResponse,
  body: Buffer | string,
  headers?: OutgoingHttpHeaders
) {
  res.writeHead(STATUS_OK, headers);
  res.write(body);
  res.end();
}

function handleAddresses(
  req: IncomingMessage,
  res: ServerResponse,
  cb: Callback
) {
  if (req.headers['content-type'] !== applicationJson) {
    invalidRequest(
      req,
      res,
      `Invalid content type: ${req.headers['content-type']}`
    );
    return;
  }
  let data = '';
  req.on('data', chunk => {
    data += chunk;
  });
  req.on('end', () => {
    try {
      const payload = JSON.parse(data);
      if (!('addresses' in payload) || !Array.isArray(payload.addresses)) {
        invalidRequest(req, res, 'Invalid request schema');
        return;
      }
      cb(payload.addresses);
      res.writeHead(STATUS_OK);
      res.end();
    } catch (e) {
      invalidRequest(req, res, 'Malformed JSON');
    }
  });
}

function serveFile(req: IncomingMessage, res: ServerResponse, paths: string) {
  const url = req.url!!;
  if (!url.endsWith('.svg') && !url.endsWith('.ico')) {
    invalidRequest(
      req,
      res,
      `Access to file is not allowed ${req.url}`,
      STATUS_FORBIDDEN
    );
    return;
  }
  const filePath = path.join(paths, url);
  const s = path.extname(filePath);
  let contentType = null;
  if (s.includes('svg')) {
    contentType = 'image/svg+xml';
  } else if (s.includes('ico')) {
    contentType = 'image/vnd.microsoft.icon';
  }
  okResponse(
    req,
    res,
    fs.readFileSync(filePath),
    contentType ? { 'Content-Type': contentType } : undefined
  );
}

function handleRequests(
  req: IncomingMessage,
  res: ServerResponse,
  cb: Callback
) {
  const contentLengthHeader = req.headers['content-length'];
  if (contentLengthHeader) {
    try {
      const contentLength = parseInt(contentLengthHeader);
      if (contentLength > 524288) {
        invalidRequest(
          req,
          res,
          'Only requests up to 0.5MB are allowed',
          STATUS_BAD_REQUEST
        );
        return;
      }
    } catch (e) {
      invalidRequest(
        req,
        res,
        'No valid content length',
        STATUS_CONTENT_LENGTH_REQUIRED
      );
      return;
    }
  }
  const paths =
    process.env.NODE_ENV === 'development'
      ? path.join(__dirname, '..', 'public')
      : __dirname;
  if (req.url && req.url === '/') {
    okResponse(
      req,
      res,
      fs.readFileSync(path.join(paths, 'import.html')),
      headersHtml
    );
  } else if (req.url && req.url === '/import' && req.method === 'POST') {
    handleAddresses(req, res, cb);
    stopHttp();
  } else if (req.url && fs.existsSync(path.join(paths, req.url))) {
    serveFile(req, res, paths);
  } else {
    invalidRequest(
      req,
      res,
      `${req.url} was not found on server`,
      STATUS_NOT_FOUND
    );
  }
}

export function startHttp(cb: Callback, port: number = 43432) {
  if (server && server.listening) {
    throw new Error(`http server is already listening at: ${server.address()}`);
  }
  console.log(`Metamask Import Server: Listening at: http://localhost:${port}`);
  server = http.createServer((req, resp) => handleRequests(req, resp, cb));
  server.listen(port);
  return server.address();
}

export function stopHttp() {
  console.log('Metamask Import Server: Stopped');
  if (server && server.listening) {
    server.close();
  }
}
