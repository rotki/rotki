import { mount, RouterLinkStub, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import DockSyncHint from '@/modules/task-center/components/DockSyncHint.vue';

const loading = ref<boolean>(false);
const etherscanKey = ref<string>('');

vi.mock('@/modules/settings/api-keys/external/use-external-api-keys', () => ({
  useExternalApiKeys: (): { loading: Ref<boolean>; useApiKey: () => Ref<string> } => ({ loading, useApiKey: () => etherscanKey }),
}));

function createWrapper(): VueWrapper {
  return mount(DockSyncHint, { global: { stubs: { RouterLink: RouterLinkStub } } });
}

describe('dockSyncHint', () => {
  it('should explain the first sync, and point to adding an Etherscan key when none is set', () => {
    set(loading, false);
    set(etherscanKey, '');

    const wrapper = createWrapper();

    expect(wrapper.text()).toContain('task_dock.sync_hint.explanation');
    expect(wrapper.text()).toContain('task_dock.sync_hint.etherscan');
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toEqual({ name: '/api-keys/external/' });
  });

  it('should leave out the Etherscan tip for someone who already has a key', () => {
    set(loading, false);
    set(etherscanKey, 'a-key');

    const wrapper = createWrapper();

    expect(wrapper.text()).toContain('task_dock.sync_hint.explanation');
    expect(wrapper.find('[data-testid=dock-sync-hint-etherscan]').exists()).toBe(false);
  });

  it('should hold the Etherscan tip back while the keys are still loading, so it does not flash', () => {
    set(loading, true);
    set(etherscanKey, '');

    expect(createWrapper().text()).not.toContain('task_dock.sync_hint.etherscan');
  });
});
