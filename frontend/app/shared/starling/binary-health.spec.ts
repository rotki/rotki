import path from 'node:path';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { findUnusableBinary } from './binary-health';
import { BinaryComponent, BinaryStatus, type UnusableBinary } from './binary-types';

const RESOURCES = '/opt/rotki/resources';

const { accessSyncMock, existsSyncMock, findCoreBinaryMock, platformState } = vi.hoisted(() => ({
  accessSyncMock: vi.fn<(target: string, mode?: number) => void>(),
  existsSyncMock: vi.fn<(target: string) => boolean>(),
  findCoreBinaryMock: vi.fn<(directory: string) => { binary: string; dir: string } | undefined>(),
  platformState: { platform: 'linux' },
}));

vi.mock('node:process', async (importOriginal) => {
  const actual = await importOriginal<{ default: NodeJS.Process }>();
  const proxy = new Proxy(actual.default, {
    get: (target, key): unknown => (key === 'platform' ? platformState.platform : Reflect.get(target, key)),
  });
  return { ...actual, default: proxy };
});

vi.mock('node:fs', () => ({
  default: { accessSync: accessSyncMock, constants: { X_OK: 1 }, existsSync: existsSyncMock },
}));

vi.mock('./starling-paths', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./starling-paths')>();
  return {
    ...actual,
    findCoreBinary: findCoreBinaryMock,
    packagedBackendDirectory: (): string => path.join(RESOURCES, 'backend'),
    resourcesDir: (): string => RESOURCES,
  };
});

vi.mock('./starling-launchers', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./starling-launchers')>();
  return {
    ...actual,
    resolvePackagedColibri: (): { binary: string; dir: string } => ({
      binary: path.join(RESOURCES, 'colibri', 'colibri'),
      dir: path.join(RESOURCES, 'colibri'),
    }),
    resolveStarlingBinary: (): string => path.join(RESOURCES, 'starling', 'starling'),
  };
});

const STARLING = path.join(RESOURCES, 'starling', 'starling');
const COLIBRI = path.join(RESOURCES, 'colibri', 'colibri');
const BACKEND = path.join(RESOURCES, 'backend');
const CORE = path.join(BACKEND, 'rotki-core', 'rotki-core-1.44.0');
const UPGRADED_CORE = path.join(BACKEND, 'rotki-core', 'rotki-core-1.44.1');

function unusable(component: BinaryComponent, target: string, status: BinaryStatus): UnusableBinary {
  return { component, onWindows: false, path: target, status };
}

describe('findUnusableBinary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    platformState.platform = 'linux';
    existsSyncMock.mockReturnValue(true);
    accessSyncMock.mockReturnValue(undefined);
    findCoreBinaryMock.mockReturnValue({ binary: CORE, dir: path.dirname(CORE) });
  });

  it('should report nothing when every packaged binary is there and runnable', () => {
    expect(findUnusableBinary()).toBeUndefined();
  });

  it('should name a quarantined colibri and its path', () => {
    existsSyncMock.mockImplementation((target: string) => target !== COLIBRI);

    expect(findUnusableBinary()).toStrictEqual(unusable(BinaryComponent.COLIBRI, COLIBRI, BinaryStatus.MISSING));
  });

  it('should report a binary that is present but cannot be executed', () => {
    accessSyncMock.mockImplementation((target: string) => {
      if (target === COLIBRI)
        throw new Error('EACCES');
    });

    expect(findUnusableBinary()).toStrictEqual(unusable(BinaryComponent.COLIBRI, COLIBRI, BinaryStatus.NOT_EXECUTABLE));
  });

  it('should report starling first, since a missing supervisor reports nothing itself', () => {
    existsSyncMock.mockReturnValue(false);

    expect(findUnusableBinary()).toStrictEqual(unusable(BinaryComponent.STARLING, STARLING, BinaryStatus.MISSING));
  });

  it('should mark a report made on Windows, so the recovery steps can name Windows Security', () => {
    platformState.platform = 'win32';
    existsSyncMock.mockImplementation((target: string) => target !== COLIBRI);

    expect(findUnusableBinary()).toStrictEqual({ ...unusable(BinaryComponent.COLIBRI, COLIBRI, BinaryStatus.MISSING), onWindows: true });
  });

  it('should report the searched directory when no core binary resolves', () => {
    findCoreBinaryMock.mockReturnValue(undefined);

    expect(findUnusableBinary()).toStrictEqual(unusable(BinaryComponent.CORE, BACKEND, BinaryStatus.MISSING));
  });

  it('should report a resolved core binary that has since gone', () => {
    existsSyncMock.mockImplementation((target: string) => target !== CORE);

    expect(findUnusableBinary()).toStrictEqual(unusable(BinaryComponent.CORE, CORE, BinaryStatus.MISSING));
  });

  it('should report a core directory that cannot be read, as security software locking it looks', () => {
    findCoreBinaryMock.mockImplementation(() => {
      throw Object.assign(new Error('EACCES: permission denied, scandir'), { code: 'EACCES' });
    });

    expect(findUnusableBinary()).toStrictEqual(unusable(BinaryComponent.CORE, BACKEND, BinaryStatus.NOT_EXECUTABLE));
  });

  it('should pass over an ambiguous core install instead of throwing, and still inspect colibri', () => {
    findCoreBinaryMock.mockImplementation(() => {
      throw new Error('Expected one rotki-core binary but found: rotki-core-1.44.0, rotki-core-1.45.0');
    });
    existsSyncMock.mockImplementation((target: string) => target !== COLIBRI);

    expect(findUnusableBinary()).toStrictEqual(unusable(BinaryComponent.COLIBRI, COLIBRI, BinaryStatus.MISSING));
  });

  it('should check the core starling was launched with, not whichever an upgrade left in the directory', () => {
    findCoreBinaryMock.mockReturnValue({ binary: UPGRADED_CORE, dir: path.dirname(UPGRADED_CORE) });
    existsSyncMock.mockImplementation((target: string) => target !== CORE);

    expect(findUnusableBinary(CORE)).toStrictEqual(unusable(BinaryComponent.CORE, CORE, BinaryStatus.MISSING));
    expect(findCoreBinaryMock).not.toHaveBeenCalled();
  });
});
