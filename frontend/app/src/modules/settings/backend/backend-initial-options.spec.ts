import type { BackendOptions } from '@shared/ipc';
import type { BackendConfiguration, DefaultBackendArguments } from '@/modules/shell/app/backend';
import { LogLevel } from '@shared/log-level';
import { describe, expect, it } from 'vitest';
import { type BackendOptionFallbacks, resolveInitialBackendOptions } from './backend-initial-options';

const defaults: DefaultBackendArguments = {
  maxLogfilesNum: 3,
  maxSizeInMbAllLogs: 300,
  sqliteInstructions: 5000,
};

const fallbacks: BackendOptionFallbacks = {
  dataDirectory: '/fallback/data',
  logDirectory: '/fallback/logs',
  defaultLogLevel: LogLevel.CRITICAL,
  defaults,
};

function makeConfiguration(): BackendConfiguration {
  return {
    loglevel: { value: LogLevel.INFO, isDefault: true },
    maxLogfilesNum: { value: 7, isDefault: false },
    maxSizeInMbAllLogs: { value: 500, isDefault: false },
    sqliteInstructions: { value: 9000, isDefault: false },
  };
}

describe('resolveInitialBackendOptions', () => {
  it('should fall back to defaults when neither options nor configuration are set', () => {
    expect(resolveInitialBackendOptions({}, undefined, fallbacks)).toStrictEqual({
      dataDirectory: '/fallback/data',
      logDirectory: '/fallback/logs',
      logFromOtherModules: false,
      loglevel: LogLevel.CRITICAL,
      maxLogfilesNum: 3,
      maxSizeInMbAllLogs: 300,
      sqliteInstructions: 5000,
    });
  });

  it('should use configuration values over the fallbacks for config-backed fields', () => {
    expect(resolveInitialBackendOptions({}, makeConfiguration(), fallbacks)).toStrictEqual({
      dataDirectory: '/fallback/data',
      logDirectory: '/fallback/logs',
      logFromOtherModules: false,
      loglevel: LogLevel.INFO,
      maxLogfilesNum: 7,
      maxSizeInMbAllLogs: 500,
      sqliteInstructions: 9000,
    });
  });

  it('should let persisted options win over both configuration and fallbacks', () => {
    const options: Partial<BackendOptions> = {
      dataDirectory: '/user/data',
      logDirectory: '/user/logs',
      logFromOtherModules: true,
      loglevel: LogLevel.DEBUG,
      maxLogfilesNum: 10,
      maxSizeInMbAllLogs: 999,
      sqliteInstructions: 12345,
    };
    expect(resolveInitialBackendOptions(options, makeConfiguration(), fallbacks)).toStrictEqual(options);
  });

  it('should resolve each field independently along the option → config → fallback chain', () => {
    const options: Partial<BackendOptions> = {
      dataDirectory: '/user/data',
      maxLogfilesNum: 10,
    };
    expect(resolveInitialBackendOptions(options, makeConfiguration(), fallbacks)).toStrictEqual({
      dataDirectory: '/user/data', // from options
      logDirectory: '/fallback/logs', // from fallbacks (no option, no config field)
      logFromOtherModules: false,
      loglevel: LogLevel.INFO, // from configuration
      maxLogfilesNum: 10, // from options
      maxSizeInMbAllLogs: 500, // from configuration
      sqliteInstructions: 9000, // from configuration
    });
  });

  it('should keep an explicit false logFromOtherModules from options', () => {
    const result = resolveInitialBackendOptions({ logFromOtherModules: false }, undefined, fallbacks);
    expect(result.logFromOtherModules).toBe(false);
  });
});
