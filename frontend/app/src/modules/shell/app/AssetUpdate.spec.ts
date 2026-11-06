import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AssetUpdate from '@/modules/shell/app/AssetUpdate.vue';
import AssetUpdateInlineConfirm from '@/modules/shell/app/AssetUpdateInlineConfirm.vue';

const { inlineConfirm, updateComplete } = await vi.hoisted(async () => {
  const { shallowRef } = await import('vue');
  return {
    inlineConfirm: shallowRef<boolean>(false),
    updateComplete: vi.fn<() => Promise<void>>(async () => Promise.resolve()),
  };
});

vi.mock('@/modules/shell/app/use-asset-update', async () => {
  const { computed, ref, shallowRef } = await import('vue');
  return {
    useAssetUpdate: (): Record<string, unknown> => ({
      applying: shallowRef<boolean>(false),
      check: vi.fn(),
      checking: shallowRef<boolean>(false),
      conflicts: ref([]),
      inlineConfirm,
      modelChanges: ref({ changes: 0, local: 1, remote: 2, upToVersion: 2 }),
      modelShowConflictDialog: shallowRef<boolean>(false),
      showUpdateDialog: shallowRef<boolean>(false),
      skip: vi.fn(),
      skipped: shallowRef<number>(0),
      status: computed(() => null),
      updateAssets: vi.fn(),
      updateComplete,
    }),
  };
});

describe('assetUpdate', () => {
  function createWrapper(headless: boolean): VueWrapper<InstanceType<typeof AssetUpdate>> {
    return mount(AssetUpdate, {
      global: { stubs: { AssetUpdateSetting: true } },
      props: { headless },
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(inlineConfirm, false);
  });

  it('should show nothing about a finished update until one finished', () => {
    const wrapper = createWrapper(false);

    expect(wrapper.findComponent(AssetUpdateInlineConfirm).exists()).toBe(false);
  });

  it.each([false, true])('should report a finished update in place and restart on OK (headless: %s)', async (headless) => {
    set(inlineConfirm, true);
    const wrapper = createWrapper(headless);
    const done = wrapper.findComponent(AssetUpdateInlineConfirm);

    expect(done.text()).toContain('asset_update.success.title');

    await done.find('button').trigger('click');

    expect(updateComplete).toHaveBeenCalledOnce();
  });
});
