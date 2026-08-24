import { LogLevel } from '@shared/log-level';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { loadConfig } from './config';

const { existsSync, readFileSync } = vi.hoisted(() => ({
  existsSync: vi.fn(),
  readFileSync: vi.fn(),
}));

vi.mock('node:fs', () => ({
  default: { existsSync, readFileSync },
}));

describe('loadConfig', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return empty options when the config file does not exist', () => {
    existsSync.mockReturnValue(false);
    expect(loadConfig()).toStrictEqual({});
    expect(readFileSync).not.toHaveBeenCalled();
  });

  it('should map every recognized key to its option', () => {
    existsSync.mockReturnValue(true);
    readFileSync.mockReturnValue(JSON.stringify({
      'loglevel': LogLevel.DEBUG,
      'logfromothermodules': true,
      'log-dir': '/var/log',
      'data-dir': '/data',
      'max_size_in_mb_all_logs': '30',
      'max_logfiles_num': '5',
      'sqlite_instructions': '1000',
    }));

    expect(loadConfig()).toStrictEqual({
      loglevel: LogLevel.DEBUG,
      logFromOtherModules: true,
      logDirectory: '/var/log',
      dataDirectory: '/data',
      maxSizeInMbAllLogs: 30,
      maxLogfilesNum: 5,
      sqliteInstructions: 1000,
    });
  });

  it('should ignore an unrecognized loglevel', () => {
    existsSync.mockReturnValue(true);
    readFileSync.mockReturnValue(JSON.stringify({ loglevel: 'not-a-level' }));
    expect(loadConfig()).toStrictEqual({});
  });

  it('should coerce logfromothermodules to a strict boolean', () => {
    existsSync.mockReturnValue(true);
    readFileSync.mockReturnValue(JSON.stringify({ logfromothermodules: 'yes' }));
    expect(loadConfig()).toStrictEqual({ logFromOtherModules: false });
  });

  it('should return empty options when the file is malformed JSON', () => {
    existsSync.mockReturnValue(true);
    readFileSync.mockReturnValue('{ not valid json');
    expect(loadConfig()).toStrictEqual({});
  });

  it('should only include keys present in the file', () => {
    existsSync.mockReturnValue(true);
    readFileSync.mockReturnValue(JSON.stringify({ 'data-dir': '/only-data' }));
    expect(loadConfig()).toStrictEqual({ dataDirectory: '/only-data' });
  });

  describe('instance data directory', () => {
    afterEach(() => {
      vi.unstubAllEnvs();
    });

    it('should take the data directory from the instance env when there is no config file', () => {
      existsSync.mockReturnValue(false);
      vi.stubEnv('ROTKI_INSTANCE_DATA_DIR', '/instances/scratch');

      expect(loadConfig()).toStrictEqual({ dataDirectory: '/instances/scratch' });
    });

    it('should let the instance data directory win over the config file', () => {
      // An instance exists so as not to touch the shared data directory, so the file must not be
      // able to pull it back onto one. This is the case that failed: ports were isolated, the data
      // directory was not, and the run died on the shared lock.
      existsSync.mockReturnValue(true);
      readFileSync.mockReturnValue(JSON.stringify({ 'data-dir': '/shared/develop_data' }));
      vi.stubEnv('ROTKI_INSTANCE_DATA_DIR', '/instances/scratch');

      expect(loadConfig()).toStrictEqual({ dataDirectory: '/instances/scratch' });
    });

    it('should apply the instance data directory even when the config file is malformed', () => {
      existsSync.mockReturnValue(true);
      readFileSync.mockReturnValue('{ not valid json');
      vi.stubEnv('ROTKI_INSTANCE_DATA_DIR', '/instances/scratch');

      expect(loadConfig()).toStrictEqual({ dataDirectory: '/instances/scratch' });
    });

    it('should keep the other config keys when the instance overrides the data directory', () => {
      existsSync.mockReturnValue(true);
      readFileSync.mockReturnValue(JSON.stringify({ 'data-dir': '/shared', 'log-dir': '/var/log' }));
      vi.stubEnv('ROTKI_INSTANCE_DATA_DIR', '/instances/scratch');

      expect(loadConfig()).toStrictEqual({ dataDirectory: '/instances/scratch', logDirectory: '/var/log' });
    });

    it('should leave the config file in charge when the env var is empty', () => {
      // An empty string is how an unset instance reaches a child process, and it must not blank out
      // a configured data directory.
      existsSync.mockReturnValue(true);
      readFileSync.mockReturnValue(JSON.stringify({ 'data-dir': '/configured' }));
      vi.stubEnv('ROTKI_INSTANCE_DATA_DIR', '');

      expect(loadConfig()).toStrictEqual({ dataDirectory: '/configured' });
    });
  });
});
