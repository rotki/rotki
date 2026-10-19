import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { provideTableSelectionCollapsed } from '@/modules/core/table/table-selection-collapse';
import TableSelectionAction from '@/modules/core/table/TableSelectionAction.vue';

interface Props {
  disabled?: boolean;
  loading?: boolean;
}

function createWrapper(collapsed: boolean | undefined, props: Props = {}): VueWrapper {
  return mount({
    components: { TableSelectionAction },
    setup() {
      if (collapsed !== undefined)
        provideTableSelectionCollapsed(ref<boolean>(collapsed));
      return { props };
    },
    template: '<TableSelectionAction icon="lu-eye-off" color="error" data-testid="action" v-bind="props">Ignore</TableSelectionAction>',
  }, { global: { provide: libraryDefaults } });
}

function buttonProps(wrapper: VueWrapper): Record<string, unknown> {
  return wrapper.findComponent({ name: 'RuiButton' }).props();
}

describe('modules/core/table/TableSelectionAction', () => {
  it('should render as an outlined bar button outside any bar', () => {
    expect(buttonProps(createWrapper(undefined))).toMatchObject({ color: 'error', variant: 'outlined' });
  });

  it('should render as a menu entry when the bar collapsed', () => {
    expect(buttonProps(createWrapper(true))).toMatchObject({ color: 'error', variant: 'list' });
  });

  it('should emit click and keep its test id in either form', async () => {
    for (const collapsed of [false, true]) {
      const wrapper = createWrapper(collapsed);

      await wrapper.find('[data-testid="action"]').trigger('click');

      expect(wrapper.findComponent(TableSelectionAction).emitted('click')).toHaveLength(1);
    }
  });

  it('should disable the menu entry while loading, since a list button shows no spinner', () => {
    expect(buttonProps(createWrapper(true, { loading: true }))).toMatchObject({ disabled: true });
    expect(buttonProps(createWrapper(false, { loading: true }))).toMatchObject({ disabled: false, loading: true });
  });
});
