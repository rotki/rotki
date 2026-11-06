import type { useRestoreAssetDb } from '@/modules/assets/admin/use-restore-asset-db';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import ConfirmMenu from '@/modules/shell/components/ConfirmMenu.vue';
import RestoreAssetDbButton from './RestoreAssetDbButton.vue';

const { restoreAssets } = vi.hoisted(() => ({
  restoreAssets: vi.fn<(type: 'soft' | 'hard') => Promise<void>>(async () => {}),
}));

vi.mock('@/modules/assets/admin/use-restore-asset-db', () => ({
  useRestoreAssetDb: (): ReturnType<typeof useRestoreAssetDb> => ({
    loading: ref<boolean>(false),
    restoreAssets,
    restoreQuestion: type => ({ confirmLabel: `${type} reset`, message: `${type} reset?\n\nshared database`, title: 'Reset assets database', tone: 'error' }),
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

function createWrapper(): VueWrapper<InstanceType<typeof RestoreAssetDbButton>> {
  return mount(RestoreAssetDbButton, { global: { stubs: { RuiMenu } } });
}

/** The dropdown form inside the open `ConfirmMenu` that asks its questions. */
function createDropdown(): { wrapper: VueWrapper; open: Ref<boolean> } {
  const open = ref<boolean>(true);
  const wrapper = mount({
    components: { ConfirmMenu, RestoreAssetDbButton },
    setup: () => ({ open }),
    template: '<ConfirmMenu v-model="open"><RestoreAssetDbButton dropdown /></ConfirmMenu>',
  }, { global: { stubs: { RuiMenu } } });
  return { open, wrapper };
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

    it('should ask in the menu, in place of the entries, before resetting', async () => {
      const { wrapper } = createDropdown();

      await pick(wrapper, 'soft');

      expect(wrapper.find('[data-testid=inline-confirm]').text()).toContain('soft reset?');
      expect(wrapper.find('[data-testid=confirm-menu-entries]').attributes('style')).toContain('display: none');
      expect(restoreAssets).not.toHaveBeenCalled();
    });

    it('should close the menu and run the picked reset once accepted', async () => {
      const { open, wrapper } = createDropdown();

      await pick(wrapper, 'hard');
      await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

      expect(restoreAssets).toHaveBeenCalledExactlyOnceWith('hard');
      expect(get(open)).toBe(false);
    });

    it('should not reset when cancelled, and offer the entry again', async () => {
      const { open, wrapper } = createDropdown();

      await pick(wrapper, 'hard');
      await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');

      expect(restoreAssets).not.toHaveBeenCalled();
      expect(get(open)).toBe(true);
      expect(wrapper.find('[data-testid=confirm-menu-entries]').attributes('style') ?? '').not.toContain('display: none');
    });
  });
});
