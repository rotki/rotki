import type { LocationQuery } from 'vue-router';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ref, type Ref } from 'vue';
import GroupedImport from '@/modules/user-data/GroupedImport.vue';
import '@test/i18n';

const route = ref<{ query: LocationQuery }>({ query: {} });

vi.mock('vue-router', () => ({
  useRoute: (): Ref<{ query: LocationQuery }> => route,
}));

describe('grouped-import', () => {
  let wrapper: VueWrapper<InstanceType<typeof GroupedImport>>;

  afterEach(() => {
    wrapper?.unmount();
    set(route, { query: {} });
  });

  it('should preselect the source from the route query', () => {
    set(route, { query: { source: 'binance' } });
    wrapper = mount(GroupedImport, {
      global: {
        stubs: {
          RuiAutoComplete: {
            props: ['modelValue'],
            template: '<div><span data-testid="selected-source">{{ modelValue?.key }}</span></div>',
          },
        },
      },
    });

    expect(wrapper.find('[data-testid="selected-source"]').text()).toBe('binance');
  });
});
