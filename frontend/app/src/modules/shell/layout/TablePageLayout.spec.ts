import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import TablePageLayout from './TablePageLayout.vue';

function createWrapper(props: { title?: string[]; hideHeader?: boolean; child?: boolean } = {}, slots: Record<string, string> = {}): VueWrapper {
  return mount(TablePageLayout, {
    global: { stubs: { RuiIcon: true } },
    props,
    slots,
  });
}

/** The breadcrumb entries, as the rendered spans read. */
function crumbs(wrapper: VueWrapper): string[] {
  return wrapper.findAll('.text-rui-text > span').map(span => span.text());
}

describe('tablePageLayout', () => {
  it('should render every title entry, the last as the current page and the rest as steps', () => {
    const wrapper = createWrapper({ title: ['Balances', 'Blockchain', 'Ethereum'] });

    expect(crumbs(wrapper)).toEqual(['Balances', 'Blockchain', 'Ethereum']);
  });

  it('should follow all but the last entry with a separator', () => {
    const wrapper = createWrapper({ title: ['Balances', 'Blockchain', 'Ethereum'] });
    const spans = wrapper.findAll('.text-rui-text > span');

    expect(spans[0].findComponent({ name: 'RuiIcon' }).exists()).toBe(true);
    expect(spans[1].findComponent({ name: 'RuiIcon' }).exists()).toBe(true);
    expect(spans[2].findComponent({ name: 'RuiIcon' }).exists()).toBe(false);
  });

  it('should render only the last entry as the current page, carrying the filled pill', () => {
    const wrapper = createWrapper({ title: ['Balances', 'Blockchain'] });
    const spans = wrapper.findAll('.text-rui-text > span');

    expect(spans[0].classes()).not.toContain('rounded-md');
    expect(spans[1].classes()).toContain('rounded-md');
  });

  it('should render a single entry as the current page with no dangling separator', () => {
    const wrapper = createWrapper({ title: ['Dashboard'] });
    const spans = wrapper.findAll('.text-rui-text > span');

    expect(spans).toHaveLength(1);
    expect(spans[0].classes()).toContain('rounded-md');
    expect(spans[0].findComponent({ name: 'RuiIcon' }).exists()).toBe(false);
  });

  it('should render no header at all when it is hidden', () => {
    const wrapper = createWrapper({ hideHeader: true, title: ['Dashboard'] });

    expect(crumbs(wrapper)).toEqual([]);
  });

  it('should let the title slot replace the derived breadcrumb', () => {
    const wrapper = createWrapper({ title: ['Balances'] }, { title: '<span data-testid="own">Custom</span>' });

    expect(wrapper.find('[data-testid=own]').exists()).toBe(true);
    expect(crumbs(wrapper)).toEqual(['Custom']);
  });
});
