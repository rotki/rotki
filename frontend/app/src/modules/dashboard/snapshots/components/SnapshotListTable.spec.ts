import type { SnapshotListRow } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import SnapshotListTable from '@/modules/dashboard/snapshots/components/SnapshotListTable.vue';

function createRow(overrides: Partial<SnapshotListRow> = {}): SnapshotListRow {
  return {
    delta: bigNumberify(10),
    fiatPending: false,
    fiatValue: bigNumberify(100),
    ready: true,
    timestamp: 1_600_000_000,
    usdValue: bigNumberify(100),
    ...overrides,
  };
}

describe('modules/dashboard/snapshots/components/SnapshotListTable', () => {
  let wrapper: VueWrapper<InstanceType<typeof SnapshotListTable>>;

  function createWrapper(rows: SnapshotListRow[]): VueWrapper<InstanceType<typeof SnapshotListTable>> {
    return mount(SnapshotListTable, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
      },
      props: { rows },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should emit open with the row timestamp', async () => {
    wrapper = createWrapper([createRow({ timestamp: 1_600_000_000 })]);

    await wrapper.find('[data-testid=snapshot-open]').trigger('click');

    expect(wrapper.emitted('open')).toEqual([[1_600_000_000]]);
  });

  it('should emit export and delete with the row timestamp', async () => {
    wrapper = createWrapper([createRow({ timestamp: 1_600_000_000 })]);

    await wrapper.find('[data-testid=snapshot-export]').trigger('click');
    await wrapper.find('[data-testid=snapshot-delete]').trigger('click');

    expect(wrapper.emitted('export')).toEqual([[1_600_000_000]]);
    expect(wrapper.emitted('delete')).toEqual([[1_600_000_000]]);
  });

  it('should render a skeleton while the historic rate is pending', () => {
    wrapper = createWrapper([createRow({ fiatPending: true, ready: false })]);

    expect(wrapper.find('.animate-pulse').exists()).toBe(true);
  });

  it('should render a dash when there is no delta', () => {
    wrapper = createWrapper([createRow({ delta: undefined })]);

    expect(wrapper.text()).toContain('—');
  });
});
