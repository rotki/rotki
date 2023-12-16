import { type VueWrapper, mount } from '@vue/test-utils';
import { createVuetify } from 'vuetify';
import FilterEntry from '@/components/table-filter/FilterEntry.vue';
import type { SearchMatcher } from '@/types/filtering';

describe('table-filter/FilterEntry.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof FilterEntry>>;
  const createWrapper = (props: {
    matcher: SearchMatcher<any>;
    active: boolean;
  }) => {
    const vuetify = createVuetify();
    return mount(FilterEntry, {
      global: {
        plugins: [vuetify],
      },
      props: {
        ...props,
      },
    });
  };

  const matcher: SearchMatcher<any> = {
    key: 'start',
    description: 'filter by start date',
    string: true,
    suggestions: () => [],
    validate: () => true,
  };

  it('common case', () => {
    wrapper = createWrapper({ matcher, active: false });
    expect(wrapper.find('button').text()).toBe(
      `${matcher.key}: ${matcher.description}`,
    );
    expect(wrapper.classes()).not.toMatch(/_selected_/);
  });

  it('active = true', () => {
    wrapper = createWrapper({ matcher, active: true });
    expect(wrapper.classes()).toMatch(/_selected_/);
  });
});
