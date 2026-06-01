import type { LogService } from '@electron/main/log-service';
import process from 'node:process';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { protectHtmlAssociation } from './html-mime-protection';

const { execFileSync } = vi.hoisted(() => ({ execFileSync: vi.fn() }));

vi.mock('node:child_process', () => ({ default: { execFileSync }, execFileSync }));

function createLogger(): LogService {
  return {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  } as unknown as LogService;
}

/**
 * Routes mocked xdg-mime/xdg-settings calls. `htmlHandler` is read for
 * `query default text/html` and updated by the register() callback.
 */
function mockCommands(state: { htmlHandler?: string; defaultBrowser?: string }): void {
  execFileSync.mockImplementation((command: string, args: string[]) => {
    if (command === 'xdg-mime' && args[0] === 'query')
      return `${state.htmlHandler ?? ''}\n`;

    if (command === 'xdg-mime' && args[0] === 'default') {
      state.htmlHandler = args[1];
      return '';
    }

    if (command === 'xdg-settings' && args[0] === 'get')
      return `${state.defaultBrowser ?? ''}\n`;

    return '';
  });
}

describe('protectHtmlAssociation', () => {
  const originalPlatform = process.platform;

  function setPlatform(platform: NodeJS.Platform): void {
    Object.defineProperty(process, 'platform', { value: platform, configurable: true });
  }

  beforeEach(() => {
    execFileSync.mockReset();
  });

  afterEach(() => {
    Object.defineProperty(process, 'platform', { value: originalPlatform, configurable: true });
  });

  function queryCallCount(): number {
    return execFileSync.mock.calls.filter(([command, args]) => command === 'xdg-mime' && args[0] === 'query').length;
  }

  function restoreCallCount(): number {
    return execFileSync.mock.calls.filter(([command, args]) => command === 'xdg-mime' && args[0] === 'default').length;
  }

  it('should run register without touching xdg tools on non-linux platforms', () => {
    setPlatform('darwin');
    const register = vi.fn((): boolean => true);

    protectHtmlAssociation(createLogger(), register);

    expect(register).toHaveBeenCalledOnce();
    expect(execFileSync).not.toHaveBeenCalled();
  });

  it('should not restore when registration leaves the text/html handler untouched', () => {
    setPlatform('linux');
    const state = { htmlHandler: 'firefox.desktop' };
    mockCommands(state);
    // registration runs but does not hijack text/html
    const register = vi.fn((): boolean => true);

    protectHtmlAssociation(createLogger(), register);

    expect(register).toHaveBeenCalledOnce();
    expect(state.htmlHandler).toBe('firefox.desktop');
    expect(restoreCallCount()).toBe(0);
  });

  it('should restore the previous handler when registration hijacks text/html', () => {
    setPlatform('linux');
    const state = { htmlHandler: 'firefox.desktop' };
    mockCommands(state);
    const register = vi.fn((): boolean => {
      state.htmlHandler = 'rotki.desktop';
      return true;
    });

    protectHtmlAssociation(createLogger(), register);

    expect(state.htmlHandler).toBe('firefox.desktop');
    expect(execFileSync).toHaveBeenCalledWith('xdg-mime', ['default', 'firefox.desktop', 'text/html'], expect.anything());
  });

  it('should heal an already-corrupted handler using the default web browser', () => {
    setPlatform('linux');
    // text/html is already rotki.desktop (corrupted on a previous launch) and the
    // guard skips re-registration on this launch
    const state = { htmlHandler: 'rotki.desktop', defaultBrowser: 'google-chrome.desktop' };
    mockCommands(state);
    const register = vi.fn((): boolean => false);

    protectHtmlAssociation(createLogger(), register);

    expect(state.htmlHandler).toBe('google-chrome.desktop');
    expect(execFileSync).toHaveBeenCalledWith('xdg-mime', ['default', 'google-chrome.desktop', 'text/html'], expect.anything());
  });

  it('should not attempt a restore when no sane handler can be determined', () => {
    setPlatform('linux');
    const state = { htmlHandler: 'rotki.desktop' };
    mockCommands(state); // no default browser available
    const register = vi.fn((): boolean => false);

    protectHtmlAssociation(createLogger(), register);

    expect(restoreCallCount()).toBe(0);
  });

  it('should query text/html only once when registration is skipped', () => {
    setPlatform('linux');
    const state = { htmlHandler: 'firefox.desktop' };
    mockCommands(state);
    const register = vi.fn((): boolean => false);

    protectHtmlAssociation(createLogger(), register);

    expect(queryCallCount()).toBe(1);
    expect(restoreCallCount()).toBe(0);
  });

  it('should re-check text/html after an actual registration', () => {
    setPlatform('linux');
    const state = { htmlHandler: 'firefox.desktop' };
    mockCommands(state);
    const register = vi.fn((): boolean => true);

    protectHtmlAssociation(createLogger(), register);

    expect(queryCallCount()).toBe(2);
  });

  it('should swallow errors from xdg tools and still run register', () => {
    setPlatform('linux');
    execFileSync.mockImplementation(() => {
      throw new Error('xdg-mime not found');
    });
    const register = vi.fn((): boolean => true);

    expect(() => protectHtmlAssociation(createLogger(), register)).not.toThrow();
    expect(register).toHaveBeenCalledOnce();
  });
});
