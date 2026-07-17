import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

/**
 * The quitting flag lives in a `createGlobalState` singleton with no reset, so
 * each test needs a fresh module graph to start from "not quitting".
 */
async function loadApp(): Promise<{
  App: typeof import('@/App.vue').default;
  AppQuitting: typeof import('@/modules/shell/app/AppQuitting.vue').default;
  LayoutWrapper: typeof import('@/modules/shell/layout/LayoutWrapper.vue').default;
  useAppQuitting: typeof import('@/modules/shell/app/use-app-quitting').useAppQuitting;
}> {
  vi.resetModules();
  return {
    App: (await import('@/App.vue')).default,
    AppQuitting: (await import('@/modules/shell/app/AppQuitting.vue')).default,
    LayoutWrapper: (await import('@/modules/shell/layout/LayoutWrapper.vue')).default,
    useAppQuitting: (await import('@/modules/shell/app/use-app-quitting')).useAppQuitting,
  };
}

describe('app', () => {
  it('should render the layout while not quitting', async () => {
    const { App, AppQuitting, LayoutWrapper } = await loadApp();

    const wrapper = mount(App, { shallow: true });

    expect(wrapper.findComponent(LayoutWrapper).exists()).toBe(true);
    expect(wrapper.findComponent(AppQuitting).exists()).toBe(false);
  });

  it('should swap the layout for the shutdown screen when quitting', async () => {
    const { App, AppQuitting, LayoutWrapper, useAppQuitting } = await loadApp();
    const wrapper = mount(App, { shallow: true });

    useAppQuitting().startQuitting();
    await nextTick();

    // The whole tree goes, not just the page: the notification popup lives
    // inside the layout, and it is what would surface the shutdown errors.
    expect(wrapper.findComponent(AppQuitting).exists()).toBe(true);
    expect(wrapper.findComponent(LayoutWrapper).exists()).toBe(false);
  });
});
