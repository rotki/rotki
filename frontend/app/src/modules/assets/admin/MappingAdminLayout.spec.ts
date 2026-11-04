import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import MappingAdminLayout from '@/modules/assets/admin/MappingAdminLayout.vue';

function createWrapper(loading = false): VueWrapper<InstanceType<typeof MappingAdminLayout>> {
  return mount(MappingAdminLayout, {
    global: {
      stubs: {
        AssetManagerMoreTitle: true,
        RuiButton: {
          inheritAttrs: false,
          props: { loading: { default: false, type: Boolean } },
          template: '<button v-bind="$attrs" :data-loading="loading"><slot /></button>',
        },
        RuiIcon: true,
        TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
      },
    },
    props: { addTestId: 'add-mapping', loading },
    slots: { default: '<div data-testid="content" />' },
  });
}

describe('modules/assets/admin/MappingAdminLayout', () => {
  it('should ask for a refresh from the Refresh button', async () => {
    const wrapper = createWrapper();

    await wrapper.findAll('button')[0].trigger('click');

    expect(wrapper.emitted('refresh')).toEqual([[]]);
    expect(wrapper.emitted('add')).toBeUndefined();
  });

  it('should ask to add a mapping from the button carrying the given test id', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=add-mapping]').trigger('click');

    expect(wrapper.emitted('add')).toEqual([[]]);
    expect(wrapper.emitted('refresh')).toBeUndefined();
  });

  it('should show the Refresh button loading while the table loads', () => {
    expect(createWrapper(true).findAll('button')[0].attributes('data-loading')).toBe('true');
  });

  it('should render the page content', () => {
    expect(createWrapper().find('[data-testid=content]').exists()).toBe(true);
  });
});
