import type { LogService } from '@electron/main/log-service';
import type { JsonRpcResponse } from '@electron/main/starling-handler-types';
import type { Writable } from 'node:stream';

/** Dispatch for an id-less notification (an `event.*` method + its params). */
export type StarlingNotificationHandler = (method: string, params: unknown) => void;

/**
 * The NDJSON JSON-RPC client half of the starling control channel: it correlates
 * id-tagged responses back to their pending requests and forwards id-less
 * notifications to the handler. It owns nothing about the child's lifecycle — the
 * handler `attach`es it to each spawned child's stdin and `detach`es on exit.
 */
export class StarlingRpc {
  private nextId: number = 1;
  private stdin: Writable | undefined;
  private readonly pending = new Map<number, { resolve: (value: any) => void; reject: (error: Error) => void }>();

  constructor(
    private readonly logger: LogService,
    private readonly onNotification: StarlingNotificationHandler,
  ) {}

  /** Point the client at the current child's stdin. Called once per spawn. */
  attach(stdin: Writable): void {
    this.stdin = stdin;
  }

  /** Drop the channel so later requests reject instead of writing to a dead pipe. */
  detach(): void {
    this.stdin = undefined;
  }

  /** Send a JSON-RPC request over stdin and await its correlated response. */
  async request<T = unknown>(method: string, params?: Record<string, unknown>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const stdin = this.stdin;
      if (!stdin) {
        reject(new Error('starling is not running'));
        return;
      }
      const id = this.nextId++;
      this.pending.set(id, { resolve, reject });
      const payload = JSON.stringify({ jsonrpc: '2.0', id, method, ...(params ? { params } : {}) });
      stdin.write(`${payload}\n`, (error) => {
        if (error) {
          this.pending.delete(id);
          reject(error);
        }
      });
    });
  }

  /** Parse one NDJSON line: an id-correlated response, or an event notification. */
  handleLine(line: string): void {
    const trimmed = line.trim();
    if (!trimmed)
      return;
    let message: JsonRpcResponse;
    try {
      message = JSON.parse(trimmed);
    }
    catch {
      this.logger.warn(`Ignoring non-JSON line from starling: ${trimmed}`);
      return;
    }

    if (typeof message.id === 'number') {
      const pending = this.pending.get(message.id);
      if (!pending)
        return;
      this.pending.delete(message.id);
      if (message.error)
        pending.reject(new Error(message.error.message));
      else
        pending.resolve(message.result);
      return;
    }

    if (message.method)
      this.onNotification(message.method, message.params);
  }

  /** Reject every in-flight request — the child died before replying. */
  rejectAll(error: Error): void {
    for (const { reject } of this.pending.values())
      reject(error);
    this.pending.clear();
  }
}
