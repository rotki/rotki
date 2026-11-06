import type { SnapshotListRow } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import SnapshotListTable from '@/modules/dashboard/snapshots/components/SnapshotListTable.vue';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';

/** Opens through its activator and renders its content only while open, as the real menu does. */
const RuiMenu = {
  emits: ['update:modelValue'],
  name: 'RuiMenu',
  props: ['modelValue'],
  template: `<div>
    <slot name="activator" :attrs="{ onClick: () => $emit('update:modelValue', true) }" />
    <div v-if="modelValue"><slot /></div>
  </div>`,
};

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
        stubs: { RuiMenu },
      },
      props: { pagination: { limit: 10, page: 1, total: rows.length }, rows },
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

  it('should emit export with the row timestamp', async () => {
    wrapper = createWrapper([createRow({ timestamp: 1_600_000_000 })]);

    await wrapper.find('[data-testid=snapshot-export]').trigger('click');

    expect(wrapper.emitted('export')).toEqual([[1_600_000_000]]);
  });

  it('should ask beside the delete button and emit nothing until confirmed', async () => {
    wrapper = createWrapper([createRow({ timestamp: 1_600_000_000 })]);

    await wrapper.find('[data-testid=snapshot-delete]').trigger('click');

    expect(wrapper.find('[data-testid=inline-confirm]').text()).toContain('dashboard.snapshot.delete.dialog.message');
    expect(wrapper.emitted('delete')).toBeUndefined();
  });

  it('should ask about the delete in the error tone, with a Delete button', () => {
    wrapper = createWrapper([createRow({ timestamp: 1_600_000_000 })]);

    expect(wrapper.findComponent(ConfirmPopover).props('question')).toMatchObject({
      confirmLabel: 'common.actions.delete',
      title: 'dashboard.snapshot.delete.dialog.title',
      tone: 'error',
    });
  });

  it('should emit delete with the row timestamp once confirmed', async () => {
    wrapper = createWrapper([createRow({ timestamp: 1_600_000_000 })]);

    await wrapper.find('[data-testid=snapshot-delete]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

    expect(wrapper.emitted('delete')).toEqual([[1_600_000_000]]);
  });

  it('should render the delta when the row has a predecessor', () => {
    wrapper = createWrapper([createRow()]);

    expect(wrapper.text()).not.toContain('—');
    expect(wrapper.text()).toContain('10');
  });

  it('should render a dash in the delta column for the oldest snapshot', () => {
    wrapper = createWrapper([createRow({ previousTimestamp: undefined, previousUsdValue: undefined })]);

    expect(wrapper.text()).toContain('—');
  });
});
