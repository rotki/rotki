import { type Wrapper, mount } from '@vue/test-utils';
import FilterEntry from '@/components/table-filter/FilterEntry.vue';
import type { SearchMatcher } from '@/types/filtering';

vi.mocked(useCssModule).mockReturnValue({
  selected: 'selected',
});

describe('table-filter/FilterEntry.vue', () => {
  let wrapper: Wrapper<any>;
  const createWrapper = (props: {
    matcher: SearchMatcher<any>;
    active: boolean;
  }) => mount(FilterEntry, {
    propsData: {
      ...props,
    },
  });

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
      `${matcher.key}:  ${matcher.description}`,
    );
    expect(wrapper.find('.selected').exists()).toBeFalsy();
  });

  it('active = true', () => {
    wrapper = createWrapper({ matcher, active: true });
    expect(wrapper.find('.selected').exists()).toBeTruthy();
  });
});
