import type { UnmatchedFailure, UnmatchedRowActionSpec } from '@/modules/history/events/unmatched-actions';
import type { UnmatchedMovementRow } from '@/modules/history/events/use-unmatched-movement-rows';
import { createMock } from '@test/utils/create-mock';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import UnmatchedMovementsTable from '@/modules/history/events/UnmatchedMovementsTable.vue';
import '@test/i18n';

const RuiDataTable = defineComponent({
  name: 'RuiDataTable',
  props: ['empty'],
  template: '<div><slot name="body.prepend" /><div data-testid="empty"><slot name="empty-description" /></div></div>',
});

const failure: UnmatchedFailure = { message: 'backend down', title: 'Could not load' };

function mountTable(state: { failure?: UnmatchedFailure; rows?: UnmatchedMovementRow[]; withAlert?: boolean } = {}): VueWrapper {
  return mount(UnmatchedMovementsTable, {
    global: { provide: libraryDefaults, stubs: { RuiDataTable } },
    props: {
      emptyDescription: 'empty',
      failure: state.failure,
      maxHeight: '100px',
      rows: state.rows ?? [],
      selected: [],
      specFor: () => createMock<UnmatchedRowActionSpec>(),
    },
    slots: state.withAlert ? { alert: '<div data-testid="alert-slot" />' } : {},
  });
}

describe('unmatchedMovementsTable', () => {
  it('should name a failure with no rows in the empty state, with a retry', async () => {
    const wrapper = mountTable({ failure });

    expect(wrapper.findComponent(RuiDataTable).props('empty')).toEqual({ label: 'Could not load' });
    expect(wrapper.find('[data-testid=table-failure-message]').text()).toBe('backend down');
    await wrapper.find('[data-testid=table-failure-retry]').trigger('click');

    expect(wrapper.emitted('retry')).toHaveLength(1);
  });

  it('should keep the plain empty text while nothing failed', () => {
    const wrapper = mountTable();

    expect(wrapper.findComponent(RuiDataTable).props('empty')).toEqual({ description: 'empty' });
    expect(wrapper.find('[data-testid=failure-strip]').exists()).toBe(false);
  });

  it('should name a failure in a strip above the rows an earlier load left, with a retry', async () => {
    const wrapper = mountTable({ failure, rows: [createMock<UnmatchedMovementRow>()] });

    expect(wrapper.find('[data-testid=failure-strip]').text()).toContain('backend down');
    await wrapper.find('[data-testid=failure-strip-retry]').trigger('click');

    expect(wrapper.emitted('retry')).toHaveLength(1);
  });

  it('should show no strip over an empty table, also beside the locked matching alert', () => {
    const wrapper = mountTable({ failure, withAlert: true });

    expect(wrapper.find('[data-testid=alert-slot]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=failure-strip]').exists()).toBe(false);
  });
});
