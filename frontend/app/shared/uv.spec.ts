// @vitest-environment node
import { beforeEach, describe, expect, it, vi } from 'vitest';

// Probing uv shells out, so it is mocked: these must give the same answer on a
// box with uv installed and on one without.
const { execSyncMock } = vi.hoisted(() => ({ execSyncMock: vi.fn() }));

vi.mock('node:child_process', async (importOriginal) => {
  const actual = await importOriginal<typeof import('node:child_process')>();
  return { ...actual, default: { ...actual, execSync: execSyncMock }, execSync: execSyncMock };
});

/**
 * The probe result is cached in module scope, so each case needs a fresh module
 * graph to exercise its own stub.
 */
async function loadUv(): Promise<typeof import('./uv')> {
  vi.resetModules();
  return import('./uv');
}

function uvInstalled(): void {
  execSyncMock.mockReturnValue('uv 0.9.7\n');
}

function uvMissing(): void {
  execSyncMock.mockImplementation((): never => {
    throw new Error('command not found: uv');
  });
}

describe('uvVersion', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete process.env.VIRTUAL_ENV;
  });

  it('should report the trimmed version when uv is on PATH', async () => {
    uvInstalled();
    const { uvVersion } = await loadUv();

    expect(uvVersion()).toBe('uv 0.9.7');
  });

  it('should report null when uv is not on PATH', async () => {
    uvMissing();
    const { uvVersion } = await loadUv();

    expect(uvVersion()).toBeNull();
  });

  it('should probe only once across repeated calls', async () => {
    uvInstalled();
    const { uvVersion, isUvAvailable } = await loadUv();

    uvVersion();
    uvVersion();
    isUvAvailable();

    expect(execSyncMock).toHaveBeenCalledTimes(1);
  });

  it('should not retry a probe that already failed', async () => {
    uvMissing();
    const { uvVersion } = await loadUv();

    expect(uvVersion()).toBeNull();
    expect(uvVersion()).toBeNull();
    expect(execSyncMock).toHaveBeenCalledTimes(1);
  });
});

describe('shouldUseUv', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete process.env.VIRTUAL_ENV;
  });

  it('should defer to an active virtualenv even when uv is installed', async () => {
    process.env.VIRTUAL_ENV = '/repo/.venv';
    uvInstalled();
    const { shouldUseUv } = await loadUv();

    expect(shouldUseUv()).toBe(false);
  });

  it('should not even probe uv while a virtualenv is active', async () => {
    process.env.VIRTUAL_ENV = '/repo/.venv';
    uvInstalled();
    const { shouldUseUv } = await loadUv();

    shouldUseUv();

    expect(execSyncMock).not.toHaveBeenCalled();
  });

  it('should resolve through uv when no virtualenv is active', async () => {
    uvInstalled();
    const { shouldUseUv } = await loadUv();

    expect(shouldUseUv()).toBe(true);
  });

  it('should fall back to the interpreter on PATH when uv is missing', async () => {
    uvMissing();
    const { shouldUseUv } = await loadUv();

    expect(shouldUseUv()).toBe(false);
  });
});
