import type { SearchMatcher } from '@/types/filtering';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import FilterEntry from '@/components/table-filter/FilterEntry.vue';

describe('table-filter/FilterEntry.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof FilterEntry>>;
  const createWrapper = (props: { matcher: SearchMatcher<any>; active: boolean }) =>
    mount(FilterEntry, {
      props: {
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

  afterEach(() => {
    wrapper.unmount();
  });

  it('common case', () => {
    wrapper = createWrapper({ matcher, active: false });
    expect(wrapper.find('button').text()).toBe(`${matcher.key}: ${matcher.description}`);
    expect(wrapper.classes()).not.toEqual(expect.arrayContaining([expect.stringMatching(/_selected_/)]));
  });

  it('active = true', () => {
    wrapper = createWrapper({ matcher, active: true });
    expect(wrapper.classes()).toEqual(expect.arrayContaining([expect.stringMatching(/_selected_/)]));
  });
});
