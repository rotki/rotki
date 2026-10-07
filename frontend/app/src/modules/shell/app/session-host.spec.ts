import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getCurrentInstance, nextTick } from 'vue';
import { beginSession, endSession } from '@/modules/core/session/session-lifecycle';

const { built, watched } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  const hadInstance: boolean[] = [];
  return {
    built: {
      hadInstance,
      reactions: 0,
      start: vi.fn<(restarting?: boolean) => void>(),
      stop: vi.fn<() => void>(),
    },
    watched: ref<number>(0),
  };
});

vi.mock('@/modules/shell/app/use-session-monitor', () => ({
  useSessionMonitor: (): object => {
    built.hadInstance.push(getCurrentInstance() !== null);
    watch(watched, () => {
      built.reactions += 1;
    });
    return { start: built.start, stop: built.stop };
  },
}));

/** Mounts the host against the real monitor service, which the shared setup otherwise mocks. */
async function mountHost(): Promise<ReturnType<typeof mount>> {
  vi.doUnmock('@/modules/shell/app/use-monitor-service');
  vi.resetModules();
  const { SessionHost } = await import('@/modules/shell/app/session-host');
  return mount(SessionHost);
}

describe('modules/shell/app/session-host', () => {
  beforeEach(() => {
    beginSession();
    set(watched, 0);
    built.hadInstance = [];
    built.reactions = 0;
    vi.clearAllMocks();
  });

  it('should build the monitor inside a component setup, where useI18n works', async () => {
    await mountHost();

    expect(built.hadInstance).toEqual([true]);
  });

  it('should hand the monitor it built to the monitor service', async () => {
    await mountHost();
    const { useMonitorService } = await import('@/modules/shell/app/use-monitor-service');

    useMonitorService().start();

    expect(built.start).toHaveBeenCalledWith(false);
  });

  it('should dispose the session\'s watchers the moment the session ends, before the host unmounts', async () => {
    await mountHost();
    set(watched, 1);
    await nextTick();
    expect(built.reactions).toBe(1);

    set(watched, 2);
    endSession();
    await nextTick();

    expect(built.reactions).toBe(1);
  });

  it('should withdraw the monitor when it unmounts', async () => {
    const wrapper = await mountHost();
    const { useMonitorService } = await import('@/modules/shell/app/use-monitor-service');

    wrapper.unmount();
    useMonitorService().start();

    expect(built.start).not.toHaveBeenCalled();
  });
});
