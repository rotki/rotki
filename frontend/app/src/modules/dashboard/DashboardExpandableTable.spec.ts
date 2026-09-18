import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import DashboardExpandableTable from '@/modules/dashboard/DashboardExpandableTable.vue';
import '@test/i18n';

const stubs = {
  RuiAccordion: { template: '<div><slot /></div>' },
  RuiAccordions: { props: ['modelValue'], template: '<div :data-open="modelValue === 0"><slot /></div>' },
  RuiButton: { template: '<button v-bind="$attrs"><slot /></button>' },
  RuiCard: { template: '<div><slot name="custom-header" /><slot /></div>' },
  RuiIcon: true,
};

function createWrapper(props: { count?: number } = {}): VueWrapper<InstanceType<typeof DashboardExpandableTable>> {
  return mount(DashboardExpandableTable, {
    global: { stubs },
    props,
    slots: {
      default: '<div data-testid="body" />',
      details: '<span data-testid="details" />',
      shortDetails: '<span data-testid="short-details" />',
      title: 'Assets',
      titleActions: '<span data-testid="title-action" />',
    },
  });
}

describe('dashboardExpandableTable', () => {
  it('should show the row count beside the title, before the title actions', () => {
    const wrapper = createWrapper({ count: 13 });
    const header = wrapper.html();

    expect(wrapper.get('[data-testid=dashboard-table-count]').text()).toBe('13');
    expect(header.indexOf('dashboard-table-count')).toBeLessThan(header.indexOf('title-action'));
  });

  it('should leave the count out when none is given', () => {
    expect(createWrapper().find('[data-testid=dashboard-table-count]').exists()).toBe(false);
  });

  it('should swap the details for the short details when collapsed, and back', async () => {
    const wrapper = createWrapper();
    const toggle = wrapper.get('[data-testid=dashboard-table-toggle]');

    expect(wrapper.find('[data-testid=details]').exists()).toBe(true);
    expect(toggle.attributes('aria-expanded')).toBe('true');

    await toggle.trigger('click');

    expect(wrapper.find('[data-testid=details]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=short-details]').exists()).toBe(true);
    expect(wrapper.get('[data-testid=dashboard-table-toggle]').attributes('aria-expanded')).toBe('false');
    expect(wrapper.get('[data-open]').attributes('data-open')).toBe('false');

    await wrapper.get('[data-testid=dashboard-table-toggle]').trigger('click');
    expect(wrapper.find('[data-testid=details]').exists()).toBe(true);
  });
});
