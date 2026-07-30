import type { LogService } from '@electron/main/log-service';
import { PassThrough } from 'node:stream';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it, vi } from 'vitest';
import { StarlingRpc } from './starling-rpc';

function makeLogger(): LogService {
  return createMock<LogService>({ warn: vi.fn() });
}

/** Answer each written request by feeding a response line back through the rpc. */
function autoRespond(stdin: PassThrough, rpc: StarlingRpc, reply: (id: number) => Record<string, unknown>): void {
  stdin.on('data', (chunk) => {
    const { id } = JSON.parse(chunk.toString());
    rpc.handleLine(JSON.stringify({ jsonrpc: '2.0', id, ...reply(id) }));
  });
}

describe('starlingRpc', () => {
  it('should correlate a response back to its request', async () => {
    const stdin = new PassThrough();
    const rpc = new StarlingRpc(makeLogger(), () => {});
    rpc.attach(stdin);
    autoRespond(stdin, rpc, () => ({ result: { ok: true } }));

    await expect(rpc.request('status')).resolves.toEqual({ ok: true });
  });

  it('should reject a request when the response carries an error', async () => {
    const stdin = new PassThrough();
    const rpc = new StarlingRpc(makeLogger(), () => {});
    rpc.attach(stdin);
    autoRespond(stdin, rpc, () => ({ error: { code: 1, message: 'boom' } }));

    await expect(rpc.request('start')).rejects.toThrow('boom');
  });

  it('should forward an id-less notification to the handler', () => {
    const onNotification = vi.fn();
    const rpc = new StarlingRpc(makeLogger(), onNotification);

    rpc.handleLine(JSON.stringify({ jsonrpc: '2.0', method: 'event.crashed', params: { lastError: 'x' } }));

    expect(onNotification).toHaveBeenCalledWith('event.crashed', { lastError: 'x' });
  });

  it('should reject a request once detached from the child', async () => {
    const rpc = new StarlingRpc(makeLogger(), () => {});
    rpc.attach(new PassThrough());
    rpc.detach();

    await expect(rpc.request('status')).rejects.toThrow('starling is not running');
  });

  it('should reject every in-flight request on rejectAll', async () => {
    const rpc = new StarlingRpc(makeLogger(), () => {});
    rpc.attach(new PassThrough());

    const pending = rpc.request('status');
    rpc.rejectAll(new Error('starling exited'));

    await expect(pending).rejects.toThrow('starling exited');
  });

  it('should ignore a non-JSON line and warn', () => {
    const logger = makeLogger();
    const rpc = new StarlingRpc(logger, () => {});

    rpc.handleLine('not json');

    expect(logger.warn).toHaveBeenCalled();
  });
});
