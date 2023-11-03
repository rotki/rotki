import { type Wrapper, mount } from '@vue/test-utils';
import Vuetify from 'vuetify';
import { type SearchMatcher } from '@/types/filtering';
import FilterEntry from '@/components/table-filter/FilterEntry.vue';

vi.mocked(useCssModule).mockReturnValue({
  selected: 'selected'
});

describe('table-filter/FilterEntry.vue', () => {
  let wrapper: Wrapper<any>;
  const createWrapper = (props: {
    matcher: SearchMatcher<any>;
    active: boolean;
  }) => {
    const vuetify = new Vuetify();
    return mount(FilterEntry, {
      vuetify,
      propsData: {
        ...props
      }
    });
  };

  const matcher: SearchMatcher<any> = {
    key: 'start',
    description: 'filter by start date',
    string: true,
    suggestions: () => [],
    validate: () => true
  };

  it('Common case', () => {
    wrapper = createWrapper({ matcher, active: false });
    expect(wrapper.find('button').text()).toBe(
      `${matcher.key}:  ${matcher.description}`
    );
    expect(wrapper.find('.selected').exists()).toBeFalsy();
  });

  it('active = true', () => {
    wrapper = createWrapper({ matcher, active: true });
    expect(wrapper.find('.selected').exists()).toBeTruthy();
  });
});
