import type { SearchMatcher } from '@/modules/table/filtering';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import FilterEntry from '@/components/table-filter/FilterEntry.vue';

describe('filter-entry', () => {
  let wrapper: VueWrapper<InstanceType<typeof FilterEntry>>;
  const createWrapper = (props: { matcher: SearchMatcher<any>; active: boolean }): VueWrapper<InstanceType<typeof FilterEntry>> =>
    mount(FilterEntry, {
      props: {
        ...props,
      },
    });

  const matcher: SearchMatcher<any> = {
    key: 'start',
    description: 'filter by start date',
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  };

  afterEach((): void => {
    wrapper.unmount();
  });

  it('should render common case correctly', () => {
    wrapper = createWrapper({ matcher, active: false });
    expect(wrapper.find('button').text()).toBe(`${matcher.key}: ${matcher.description}`);
    expect(wrapper.find('button').classes()).not.toContain('!bg-rui-primary-lighter/20');
  });

  it('should render active state correctly', () => {
    wrapper = createWrapper({ matcher, active: true });
    expect(wrapper.find('button').classes()).toContain('!bg-rui-primary-lighter/20');
  });
});
