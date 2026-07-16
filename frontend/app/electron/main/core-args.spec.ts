import fs from 'node:fs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RotkiCoreConfig } from './core-args';

vi.stubEnv('VITE_DEV_SERVER_URL', 'http://localhost:5173/');

describe('rotkiCoreConfig', () => {
  beforeEach((): void => {
    vi.restoreAllMocks();
    delete process.env.ROTKI_GIL;
  });

  it('should default the backend loglevel to debug in dev builds', () => {
    const { args } = RotkiCoreConfig.create(true, {}).build();
    const idx = args.indexOf('--loglevel');
    expect(idx).toBeGreaterThanOrEqual(0);
    expect(args[idx + 1]).toBe('debug');
  });

  it('should keep the GIL enabled by default for the development backend', () => {
    const { args } = RotkiCoreConfig.create(true, {}).build();
    expect(args).not.toContain('gil=0');
  });

  it('should disable the GIL when ROTKI_GIL is false', () => {
    vi.stubEnv('ROTKI_GIL', 'false');
    const { args } = RotkiCoreConfig.create(true, {}).build();
    const gilArgIndex = args.indexOf('gil=0');
    expect(args.slice(gilArgIndex - 1, gilArgIndex + 3)).toEqual([
      '-X',
      'gil=0',
      '-m',
      'rotkehlchen',
    ]);
  });

  it('should default the backend loglevel to critical in packaged builds (regression #12079)', () => {
    vi.spyOn(fs, 'existsSync').mockReturnValue(true);
    vi.spyOn(fs, 'statSync').mockReturnValue({ isDirectory: () => true } as fs.Stats);
    vi.spyOn(fs, 'readdirSync').mockReturnValue(['rotki-core-1.2.3'] as unknown as ReturnType<typeof fs.readdirSync>);

    const { args } = RotkiCoreConfig.create(false, {}).build();
    const idx = args.indexOf('--loglevel');
    expect(idx).toBeGreaterThanOrEqual(0);
    expect(args[idx + 1]).toBe('critical');
  });

  it('should honor an explicit loglevel over the resolved default', () => {
    const { args } = RotkiCoreConfig.create(true, { loglevel: 'warning' as never }).build();
    const idx = args.indexOf('--loglevel');
    expect(args[idx + 1]).toBe('warning');
  });
});
