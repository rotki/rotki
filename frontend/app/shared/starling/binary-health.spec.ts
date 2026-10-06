import path from 'node:path';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { findUnusableBinary, refusedStarling } from './binary-health';
import { BinaryComponent, BinaryPlatform, BinaryStatus, type UnusableBinary } from './binary-types';

const RESOURCES = '/opt/rotki/resources';

const { accessSyncMock, coreSearchDirectoryMock, existsSyncMock, findCoreBinaryMock, platformState } = vi.hoisted(() => ({
  accessSyncMock: vi.fn<(target: string, mode?: number) => void>(),
  coreSearchDirectoryMock: vi.fn<(directory: string) => string | undefined>(),
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
    coreSearchDirectory: coreSearchDirectoryMock,
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
const CORE_FOLDER = path.join(BACKEND, 'rotki-core');
const CORE = path.join(CORE_FOLDER, 'rotki-core-1.44.0-linux');
const UPGRADED_CORE = path.join(CORE_FOLDER, 'rotki-core-1.44.1-linux');

function unusable(component: BinaryComponent, target: string, status: BinaryStatus): UnusableBinary {
  return { component, path: target, platform: BinaryPlatform.LINUX, status };
}

function spawnError(code: string, syscall: string = 'spawn'): Error {
  return Object.assign(new Error(`${syscall} ${code}`), { code, syscall });
}

describe('findUnusableBinary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    platformState.platform = 'linux';
    existsSyncMock.mockReturnValue(true);
    accessSyncMock.mockReturnValue(undefined);
    coreSearchDirectoryMock.mockReturnValue(CORE_FOLDER);
    findCoreBinaryMock.mockReturnValue({ binary: CORE, dir: CORE_FOLDER });
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

  it.each([
    ['win32', BinaryPlatform.WINDOWS],
    ['darwin', BinaryPlatform.MACOS],
    ['linux', BinaryPlatform.LINUX],
  ])('should mark a report made on %s with its platform, which picks the recovery steps', (platform, expected) => {
    platformState.platform = platform;
    existsSyncMock.mockImplementation((target: string) => target !== COLIBRI);

    expect(findUnusableBinary()?.platform).toBe(expected);
  });

  it('should report the folder the core is looked for in when no core binary resolves', () => {
    findCoreBinaryMock.mockReturnValue(undefined);

    expect(findUnusableBinary()).toStrictEqual(unusable(BinaryComponent.CORE, CORE_FOLDER, BinaryStatus.MISSING));
  });

  it('should report the backend folder itself when not even the core folder is there', () => {
    findCoreBinaryMock.mockReturnValue(undefined);
    coreSearchDirectoryMock.mockReturnValue(undefined);

    expect(findUnusableBinary()).toStrictEqual(unusable(BinaryComponent.CORE, BACKEND, BinaryStatus.MISSING));
  });

  it('should report a resolved core binary that has since gone', () => {
    existsSyncMock.mockImplementation((target: string) => target !== CORE);

    expect(findUnusableBinary()).toStrictEqual(unusable(BinaryComponent.CORE, CORE, BinaryStatus.MISSING));
  });

  it('should report a core folder that cannot be listed as unreadable, not as a program that cannot run', () => {
    findCoreBinaryMock.mockImplementation(() => {
      throw Object.assign(new Error('EACCES: permission denied, scandir'), { code: 'EACCES' });
    });

    expect(findUnusableBinary()).toStrictEqual(unusable(BinaryComponent.CORE, BACKEND, BinaryStatus.UNREADABLE));
  });

  it('should pass over an ambiguous core install instead of throwing, and still inspect colibri', () => {
    findCoreBinaryMock.mockImplementation(() => {
      throw new Error('Expected one rotki-core binary but found: rotki-core-1.44.0-linux, rotki-core-1.45.0-linux');
    });
    existsSyncMock.mockImplementation((target: string) => target !== COLIBRI);

    expect(findUnusableBinary()).toStrictEqual(unusable(BinaryComponent.COLIBRI, COLIBRI, BinaryStatus.MISSING));
  });

  it('should report the launched core as replaced when an update put another version in its place', () => {
    findCoreBinaryMock.mockReturnValue({ binary: UPGRADED_CORE, dir: CORE_FOLDER });
    existsSyncMock.mockImplementation((target: string) => target !== CORE);

    expect(findUnusableBinary(CORE)).toStrictEqual(unusable(BinaryComponent.CORE, CORE, BinaryStatus.REPLACED));
  });

  it('should report the launched core as missing when nothing took its place', () => {
    findCoreBinaryMock.mockReturnValue(undefined);
    existsSyncMock.mockImplementation((target: string) => target !== CORE);

    expect(findUnusableBinary(CORE)).toStrictEqual(unusable(BinaryComponent.CORE, CORE, BinaryStatus.MISSING));
  });

  it('should report the launched core as missing when the folder cannot be searched for a replacement', () => {
    findCoreBinaryMock.mockImplementation(() => {
      throw new Error('Expected one rotki-core binary but found: two');
    });
    existsSyncMock.mockImplementation((target: string) => target !== CORE);

    expect(findUnusableBinary(CORE)).toStrictEqual(unusable(BinaryComponent.CORE, CORE, BinaryStatus.MISSING));
  });

  it('should not search for a replacement while the launched core is still there', () => {
    findCoreBinaryMock.mockReturnValue({ binary: UPGRADED_CORE, dir: CORE_FOLDER });

    expect(findUnusableBinary(CORE)).toBeUndefined();
    expect(findCoreBinaryMock).not.toHaveBeenCalled();
  });
});

describe('refusedStarling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    platformState.platform = 'win32';
    existsSyncMock.mockReturnValue(true);
  });

  it.each(['EPERM', 'UNKNOWN', 'EACCES'])('should report starling as not executable when its spawn fails with %s and the file is there', (code) => {
    expect(refusedStarling(spawnError(code))).toStrictEqual({
      ...unusable(BinaryComponent.STARLING, STARLING, BinaryStatus.NOT_EXECUTABLE),
      platform: BinaryPlatform.WINDOWS,
    });
  });

  it('should leave a spawn of a missing starling to the missing-file check', () => {
    existsSyncMock.mockReturnValue(false);

    expect(refusedStarling(spawnError('EPERM'))).toBeUndefined();
  });

  it('should ignore a refusal code that did not come from a spawn', () => {
    expect(refusedStarling(spawnError('EACCES', 'scandir'))).toBeUndefined();
  });

  it('should ignore spawn errors that do not mean a refusal', () => {
    expect(refusedStarling(spawnError('EMFILE'))).toBeUndefined();
    expect(refusedStarling('spawn EPERM')).toBeUndefined();
  });
});
