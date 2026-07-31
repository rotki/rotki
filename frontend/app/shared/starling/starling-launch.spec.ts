// @vitest-environment node
import type { StarlingInvocation } from './starling-args';
import { EventEmitter } from 'node:events';
import { PassThrough } from 'node:stream';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { definedOptions, requestStarlingStart, spawnStarling } from './starling-launch';
import { StarlingRpc } from './starling-rpc';

const { spawnMock } = vi.hoisted(() => ({ spawnMock: vi.fn() }));

vi.mock('node:child_process', async (importOriginal) => {
  const actual = await importOriginal<typeof import('node:child_process')>();
  return { ...actual, default: { ...actual, spawn: spawnMock }, spawn: spawnMock };
});

/** A child whose three stdio streams can be driven from the test. */
class FakeChild extends EventEmitter {
  readonly stdin = new PassThrough();
  readonly stdout = new PassThrough();
  readonly stderr = new PassThrough();
}

const invocation: StarlingInvocation = {
  command: '/repo/target/debug/starling',
  args: ['--core-port', '4242'],
  cwd: '/repo',
};

function makeRpc(): StarlingRpc {
  return new StarlingRpc({ warn: vi.fn() }, () => {});
}

function spawnOptions(): { env: NodeJS.ProcessEnv; cwd: string } {
  return spawnMock.mock.calls[0][2];
}

/** Let the readline interfaces drain what was just written. */
async function settle(): Promise<void> {
  await new Promise(resolve => setImmediate(resolve));
}

describe('spawnStarling', () => {
  let child: FakeChild;

  beforeEach(() => {
    vi.clearAllMocks();
    child = new FakeChild();
    spawnMock.mockReturnValue(child);
  });

  it('should spawn the invocation with all three streams piped', () => {
    spawnStarling({ invocation, rpc: makeRpc(), onStderr: vi.fn() });

    expect(spawnMock).toHaveBeenCalledWith(
      invocation.command,
      invocation.args,
      expect.objectContaining({ cwd: '/repo', stdio: ['pipe', 'pipe', 'pipe'] }),
    );
  });

  it('should pass the invocation env whole rather than overlaying process.env', () => {
    const env = { PATH: '/only/this' };
    spawnStarling({ invocation: { ...invocation, env }, rpc: makeRpc(), onStderr: vi.fn() });

    // Not a superset: an overlay would hand a windows child both `Path` and
    // `PATH` and let it pick which one wins.
    expect(spawnOptions().env).toEqual(env);
  });

  it('should fall back to the ambient env when the invocation carries none', () => {
    spawnStarling({ invocation, rpc: makeRpc(), onStderr: vi.fn() });

    expect(spawnOptions().env).toBe(process.env);
  });

  it('should route each stdout line into the rpc client', async () => {
    const rpc = makeRpc();
    const handleLine = vi.spyOn(rpc, 'handleLine');
    spawnStarling({ invocation, rpc, onStderr: vi.fn() });

    // One chunk carrying two whole lines and the start of a third.
    child.stdout.write('{"jsonrpc":"2.0","id":1}\n{"jsonrpc":"2.0","id":2}\n{"partial"');
    await settle();

    expect(handleLine).toHaveBeenCalledTimes(2);
    expect(handleLine).toHaveBeenNthCalledWith(1, '{"jsonrpc":"2.0","id":1}');
    expect(handleLine).toHaveBeenNthCalledWith(2, '{"jsonrpc":"2.0","id":2}');
  });

  it('should attach the rpc client to the child stdin', async () => {
    const rpc = makeRpc();
    spawnStarling({ invocation, rpc, onStderr: vi.fn() });

    const written = new Promise<string>((resolve) => {
      child.stdin.once('data', chunk => resolve(chunk.toString()));
    });
    // Nothing answers it, so it is settled by hand once the write is observed.
    const pending = rpc.request('status').catch(() => undefined);

    expect(JSON.parse(await written)).toMatchObject({ method: 'status' });

    rpc.rejectAll(new Error('test over'));
    await pending;
  });

  it('should report each stderr line to the caller', async () => {
    const onStderr = vi.fn();
    spawnStarling({ invocation, rpc: makeRpc(), onStderr });

    child.stderr.write('INFO starting\nWARN slow\n');
    await settle();

    expect(onStderr).toHaveBeenCalledWith('INFO starting');
    expect(onStderr).toHaveBeenCalledWith('WARN slow');
  });

  it('should settle exited with how the child went away', async () => {
    const { exited } = spawnStarling({ invocation, rpc: makeRpc(), onStderr: vi.fn() });

    child.emit('exit', null, 'SIGKILL');

    await expect(exited).resolves.toEqual({ code: null, signal: 'SIGKILL' });
  });

  it('should unblock an in-flight request when the child dies before replying', async () => {
    const rpc = makeRpc();
    spawnStarling({ invocation, rpc, onStderr: vi.fn() });

    const pending = rpc.request('start');
    child.emit('exit', 1, null);

    await expect(pending).rejects.toThrow('starling exited');
  });

  it('should detach the rpc client so a later request cannot write to a dead pipe', async () => {
    const rpc = makeRpc();
    spawnStarling({ invocation, rpc, onStderr: vi.fn() });

    child.emit('exit', 0, null);

    await expect(rpc.request('status')).rejects.toThrow('starling is not running');
  });

  it('should refuse a child that came back without its stdio pipes', () => {
    spawnMock.mockReturnValue(new EventEmitter());

    expect(() => spawnStarling({ invocation, rpc: makeRpc(), onStderr: vi.fn() }))
      .toThrow('starling child is missing its stdio pipes');
  });
});

describe('definedOptions', () => {
  it('should drop the options that were left unset', () => {
    expect(definedOptions({ logDirectory: '/logs', dataDirectory: undefined })).toEqual({ logDirectory: '/logs' });
  });

  it('should keep an option that is set to a falsy value', () => {
    // `false` and `0` are chosen values, not absent ones, so they must reach
    // starling — an absent field is what leaves the setting unchanged.
    expect(definedOptions({ mcpAutoStart: false, sleepSeconds: 0 })).toEqual({ mcpAutoStart: false, sleepSeconds: 0 });
  });
});

describe('requestStarlingStart', () => {
  it('should drive the bring-up with the set options and the loglevel', async () => {
    const rpc = makeRpc();
    const request = vi.spyOn(rpc, 'request').mockResolvedValue(undefined);

    await requestStarlingStart(rpc, { logDirectory: '/logs', dataDirectory: undefined }, 'debug');

    expect(request).toHaveBeenCalledWith('start', { logDirectory: '/logs', loglevel: 'debug' });
  });
});
