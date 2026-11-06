import type { useRestoreAssetDb } from '@/modules/assets/admin/use-restore-asset-db';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import RestoreAssetDbButton from './RestoreAssetDbButton.vue';

const { restoreAssets } = vi.hoisted(() => ({
  restoreAssets: vi.fn<(type: 'soft' | 'hard') => Promise<void>>(async () => {}),
}));

vi.mock('@/modules/assets/admin/use-restore-asset-db', () => ({
  useRestoreAssetDb: (): ReturnType<typeof useRestoreAssetDb> => ({
    loading: ref<boolean>(false),
    restoreAssets,
    restoreQuestion: type => ({ message: `${type} reset?\n\nshared database`, title: 'Reset assets database' }),
  }),
}));

/** Opens through its activator and renders its content only while open, as the real menu does. */
const RuiMenu = {
  name: 'RuiMenu',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: `<div>
    <slot name="activator" :attrs="{ onClick: () => $emit('update:modelValue', true) }" />
    <div v-if="modelValue"><slot /></div>
  </div>`,
};

function createWrapper(dropdown = false): VueWrapper<InstanceType<typeof RestoreAssetDbButton>> {
  return mount(RestoreAssetDbButton, {
    global: { stubs: { RuiMenu } },
    props: { dropdown },
  });
}

describe('restoreAssetDbButton', () => {
  beforeEach(() => {
    restoreAssets.mockClear();
  });

  describe('as buttons', () => {
    it.each(['soft', 'hard'] as const)('should ask beside the %s reset button, with the shared-database warning, before resetting', async (type) => {
      const wrapper = createWrapper();

      await wrapper.find(`[data-testid=asset-db-${type}-reset]`).trigger('click');

      const question = wrapper.find('[data-testid=inline-confirm]');
      expect(question.text()).toContain(`${type} reset?`);
      expect(question.text()).toContain('shared database');
      expect(restoreAssets).not.toHaveBeenCalled();
    });

    it.each(['soft', 'hard'] as const)('should run the %s reset once accepted', async (type) => {
      const wrapper = createWrapper();

      await wrapper.find(`[data-testid=asset-db-${type}-reset]`).trigger('click');
      await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

      expect(restoreAssets).toHaveBeenCalledExactlyOnceWith(type);
    });

    it('should not reset when cancelled', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=asset-db-hard-reset]').trigger('click');
      await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');

      expect(restoreAssets).not.toHaveBeenCalled();
      expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
    });
  });

  describe('as menu entries', () => {
    async function pick(wrapper: VueWrapper, type: 'soft' | 'hard'): Promise<void> {
      await wrapper.find('[data-testid=asset-db-reset-menu]').trigger('click');
      await wrapper.find(`[data-testid=asset-db-${type}-reset-item]`).trigger('click');
    }

    it('should ask in place of the entries before resetting', async () => {
      const wrapper = createWrapper(true);

      await pick(wrapper, 'soft');

      expect(wrapper.find('[data-testid=inline-confirm]').text()).toContain('soft reset?');
      expect(wrapper.find('[data-testid=asset-db-reset-menu]').exists()).toBe(false);
      expect(restoreAssets).not.toHaveBeenCalled();
    });

    it('should run the picked reset and let the menu close once accepted', async () => {
      const wrapper = createWrapper(true);

      await pick(wrapper, 'hard');
      await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

      expect(restoreAssets).toHaveBeenCalledExactlyOnceWith('hard');
      expect(wrapper.emitted('close')).toHaveLength(1);
    });

    it('should not reset when cancelled, and offer the entry again', async () => {
      const wrapper = createWrapper(true);

      await pick(wrapper, 'hard');
      await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');

      expect(restoreAssets).not.toHaveBeenCalled();
      expect(wrapper.emitted('close')).toBeUndefined();
      expect(wrapper.find('[data-testid=asset-db-reset-menu]').exists()).toBe(true);
    });
  });
});
