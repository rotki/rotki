import type { IncomingMessage } from 'node:http';
import { Buffer } from 'node:buffer';

/**
 * Reads the request body so the mock engine can inspect `async_query`. The raw
 * bytes are replayed to the backend through the proxy's `buffer` option, so the
 * forwarded request stays byte-identical to the original.
 */
export async function readBody(req: IncomingMessage): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks);
}

/** Parses the bodies the API actually sends; anything else stays unparsed. */
export function parseBody(raw: Buffer, contentType: string): unknown {
  if (raw.length === 0)
    return undefined;

  const type = contentType.toLocaleLowerCase();
  if (type.startsWith('application/json')) {
    try {
      return JSON.parse(raw.toString());
    }
    catch {
      return undefined;
    }
  }

  if (type.startsWith('application/x-www-form-urlencoded'))
    return Object.fromEntries(new URLSearchParams(raw.toString()));

  return undefined;
}
