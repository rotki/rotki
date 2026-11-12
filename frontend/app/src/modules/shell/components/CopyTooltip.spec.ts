import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import CopyTooltip from './CopyTooltip.vue';

const { copy } = vi.hoisted(() => ({ copy: vi.fn<() => Promise<void>>() }));

vi.mock('@/modules/core/common/use-clipboard', async () => {
  const { readonly, ref } = await import('vue');
  return {
    useCopy: (): { copied: Readonly<ReturnType<typeof ref<boolean>>>; copy: () => Promise<void> } => ({
      copied: readonly(ref<boolean>(false)),
      copy,
    }),
  };
});

const parentClick = vi.fn<() => void>();

function mountInClickableParent(disabled: boolean): VueWrapper {
  const Parent = defineComponent({
    setup(): () => ReturnType<typeof h> {
      return (): ReturnType<typeof h> => h('div', { 'data-testid': 'parent', 'onClick': parentClick }, [
        h(CopyTooltip, { disabled, value: '1500' }, { default: () => h('span', { 'data-testid': 'value' }, '1,500') }),
      ]);
    },
  });
  return mount(Parent, { global: { provide: libraryDefaults } });
}

describe('copyTooltip', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    copy.mockResolvedValue(undefined);
  });

  it('should copy the value on click and keep the click from the parent', async () => {
    const wrapper = mountInClickableParent(false);

    await wrapper.find('[data-testid=value]').trigger('click');

    expect(copy).toHaveBeenCalledOnce();
    expect(parentClick).not.toHaveBeenCalled();
  });

  it('should leave the click to the parent and copy nothing when disabled', async () => {
    const wrapper = mountInClickableParent(true);

    await wrapper.find('[data-testid=value]').trigger('click');

    expect(copy).not.toHaveBeenCalled();
    expect(parentClick).toHaveBeenCalledOnce();
  });
});
