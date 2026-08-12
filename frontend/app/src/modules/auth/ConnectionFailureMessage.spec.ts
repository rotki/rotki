import type { useInterop } from '@/modules/shell/app/use-electron-interop';
import { assert } from '@rotki/common';
import { LogLevel } from '@shared/log-level';
import { createMock } from '@test/utils/create-mock';
import { type DOMWrapper, flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ConnectionFailureMessage from './ConnectionFailureMessage.vue';
import '@test/i18n';

// `available` is read through VueUse's `get`, which unwraps a plain value just
// as happily as a ref — so it stays a boolean here. A `ref` cannot be built in
// `vi.hoisted`: the auto-import is not resolved yet when the factory runs.
const { control, interop, mocks, saveOptions } = vi.hoisted(() => ({
  control: {
    probe: vi.fn(async () => false),
    restart: vi.fn(async () => {}),
  },
  interop: { closeApp: vi.fn() },
  mocks: { available: false, supportsOptions: false },
  saveOptions: vi.fn(async () => {}),
}));

const connect = vi.fn();

vi.mock('@/modules/core/control/use-control', () => ({
  useControl: (): object => ({
    available: mocks.available,
    probe: control.probe,
    restart: control.restart,
    supportsOptions: mocks.supportsOptions,
  }),
}));

vi.mock('@/modules/shell/app/use-backend-connection', () => ({
  useBackendConnection: (): object => ({ connect }),
}));

vi.mock('@/modules/shell/app/use-backend-management', () => ({
  useBackendManagement: (): object => ({ saveOptions }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): ReturnType<typeof useInterop> => createMock<ReturnType<typeof useInterop>>(interop),
}));

vi.mock('@/modules/core/api/rotki-api', () => ({
  api: { defaultBackend: true, serverUrl: 'http://localhost:4242' },
}));

describe('connectionFailureMessage', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mocks.available = false;
    mocks.supportsOptions = false;
    control.probe.mockResolvedValue(false);
  });

  const createWrapper = (): VueWrapper => mount(ConnectionFailureMessage, {
    global: { stubs: { CopyTooltip: true } },
  });

  const findDebugButton = (wrapper: VueWrapper): DOMWrapper<Element> | undefined =>
    wrapper.findAll('button').find(button => button.text().includes('connection_failure.retry_with_debug'));

  function debugButton(wrapper: VueWrapper): DOMWrapper<Element> {
    const button = findDebugButton(wrapper);
    assert(button, 'the debug retry button should be rendered');
    return button;
  }

  const hasDebugButton = (wrapper: VueWrapper): boolean => findDebugButton(wrapper) !== undefined;

  /**
   * A debug retry restarts the backend *carrying a log level*, so it needs a
   * runtime that will accept one. The plain web build has neither Electron's
   * saved options nor a `/_control` endpoint, so offering the button there means
   * offering one that cannot work — it used to render and then throw on the
   * `window.interop` assertion behind it.
   */
  it('should hide the debug retry where no runtime can carry a log level', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    expect(hasDebugButton(wrapper)).toBe(false);
  });

  // Docker without a session key serves no `/_control`, so the probe says no and
  // the button must stay hidden even though this is not the plain web build.
  it('should hide the debug retry when the control endpoint is absent', async () => {
    control.probe.mockResolvedValue(false);
    mocks.available = false;

    const wrapper = createWrapper();
    await flushPromises();

    expect(hasDebugButton(wrapper)).toBe(false);
  });

  it('should offer the debug retry once the control endpoint answers', async () => {
    control.probe.mockResolvedValue(true);
    mocks.available = true;

    const wrapper = createWrapper();
    await flushPromises();

    expect(hasDebugButton(wrapper)).toBe(true);
  });

  it('should offer the debug retry on the desktop, which persists the level itself', async () => {
    mocks.supportsOptions = true;

    const wrapper = createWrapper();
    await flushPromises();

    expect(hasDebugButton(wrapper)).toBe(true);
  });

  it('should send the debug restart through control when the desktop cannot carry options', async () => {
    control.probe.mockResolvedValue(true);
    mocks.available = true;

    const wrapper = createWrapper();
    await flushPromises();
    await debugButton(wrapper).trigger('click');
    await flushPromises();

    expect(control.restart).toHaveBeenCalledWith(LogLevel.DEBUG);
    expect(saveOptions).not.toHaveBeenCalled();
    expect(connect).toHaveBeenCalled();
  });

  it('should persist the level through backend options on the desktop', async () => {
    mocks.supportsOptions = true;

    const wrapper = createWrapper();
    await flushPromises();
    await debugButton(wrapper).trigger('click');
    await flushPromises();

    expect(saveOptions).toHaveBeenCalledWith({ loglevel: LogLevel.DEBUG });
    expect(control.restart).not.toHaveBeenCalled();
    expect(connect).toHaveBeenCalled();
  });

  /**
   * This screen is reached *because* something is broken, so the restart it
   * offers is the likeliest of all to fail — the session may have lapsed, or the
   * proxy may not reach core to authorise. It still has to reconnect afterwards:
   * an unhandled rejection here would skip the retry the button is named for.
   */
  it('should still reconnect when the debug restart fails, and report why', async () => {
    control.probe.mockResolvedValue(true);
    mocks.available = true;
    control.restart.mockRejectedValue(new Error('authentication required'));

    const wrapper = createWrapper();
    await flushPromises();
    await debugButton(wrapper).trigger('click');
    await flushPromises();

    expect(connect).toHaveBeenCalled();
    expect(wrapper.text()).toContain('authentication required');
  });
});
