import type { SnapshotListRow } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import SnapshotListTable from '@/modules/dashboard/snapshots/components/SnapshotListTable.vue';

function createRow(overrides: Partial<SnapshotListRow> = {}): SnapshotListRow {
  return {
    previousTimestamp: 1_599_913_600,
    previousUsdValue: bigNumberify(90),
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

  it('should render the delta when the row has a predecessor', () => {
    // Negative control for the dash test below: the delta column is wired through
    // `previous-usd-value`, and a misspelled binding leaves every row dashed.
    wrapper = createWrapper([createRow()]);

    expect(wrapper.text()).not.toContain('—');
    expect(wrapper.text()).toContain('10');
  });

  it('should render a dash in the delta column for the oldest snapshot', () => {
    // No predecessor => no delta to show (currency defaults to USD in the test
    // harness, so no historic lookup is involved).
    wrapper = createWrapper([createRow({ previousTimestamp: undefined, previousUsdValue: undefined })]);

    expect(wrapper.text()).toContain('—');
  });
});
