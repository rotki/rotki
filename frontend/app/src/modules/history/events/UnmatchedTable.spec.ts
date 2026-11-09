import type { UnmatchedFailure, UnmatchedRowActionSpec } from '@/modules/history/events/unmatched-actions';
import type { UnmatchedRow } from '@/modules/history/events/unmatched-row';
import { createMock } from '@test/utils/create-mock';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { MOVEMENT_KIND, movementRow, plainRow, UNMATCHED_PANEL_KINDS, UnmatchedActionsStub, type UnmatchedPanelKind, untrackedRow } from '@test/utils/unmatched-panel-kinds';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import UnmatchedTable from '@/modules/history/events/UnmatchedTable.vue';
import '@test/i18n';

/** Renders each row's cells through the table's own item slots, so what a cell shows can be read. */
const RuiDataTable = defineComponent({
  name: 'RuiDataTable',
  props: ['empty', 'rows', 'cols', 'rowAttr', 'itemClass'],
  template: `
    <div>
      <slot name="body.prepend" />
      <div data-testid="empty"><slot name="empty-description" /></div>
      <div
        v-for="row in rows"
        :key="row[rowAttr]"
        data-testid="row"
        :data-key="row[rowAttr]"
        :class="itemClass(row)"
      >
        <div v-for="col in cols" :key="col.key" :data-label="col.label">
          <slot :name="'item.' + col.key" :row="row" />
        </div>
      </div>
    </div>
  `,
});

const failure: UnmatchedFailure = { cause: new Error('backend down'), message: 'backend down', title: 'Could not load' };

interface TableState {
  failure?: UnmatchedFailure;
  highlightedGroupIdentifier?: string;
  rows?: UnmatchedRow<unknown>[];
  withAlert?: boolean;
}

function mountTable(kind: UnmatchedPanelKind, state: TableState = {}): VueWrapper {
  return mount(UnmatchedTable, {
    global: {
      provide: libraryDefaults,
      stubs: { DateDisplay: true, HashLink: true, HistoryEventAsset: true, LocationDisplay: true, RuiDataTable, UnmatchedActions: UnmatchedActionsStub },
    },
    props: {
      emptyDescription: 'empty',
      variant: kind.variant,
      failure: state.failure,
      highlightedGroupIdentifier: state.highlightedGroupIdentifier,
      rows: state.rows ?? [],
      selected: [],
      specFor: () => createMock<UnmatchedRowActionSpec>(),
    },
    slots: state.withAlert ? { alert: '<div data-testid="alert-slot" />' } : {},
  });
}

function cell(wrapper: VueWrapper, key: string, label: string): ReturnType<VueWrapper['find']> {
  return wrapper.find(`[data-testid=row][data-key="${key}"] [data-label="${label}"]`);
}

describe.each(UNMATCHED_PANEL_KINDS)('unmatched table, $name', (kind) => {
  describe('failure', () => {
    it('should name a failure with no rows in the empty state, with a retry', async () => {
      const wrapper = mountTable(kind, { failure });

      expect(wrapper.findComponent(RuiDataTable).props('empty')).toEqual({ label: 'Could not load' });
      expect(wrapper.find('[data-testid=table-failure-message]').text()).toBe('backend down');
      await wrapper.find('[data-testid=table-failure-retry]').trigger('click');

      expect(wrapper.emitted('retry')).toHaveLength(1);
    });

    it('should keep the plain empty text while nothing failed', () => {
      const wrapper = mountTable(kind);

      expect(wrapper.findComponent(RuiDataTable).props('empty')).toEqual({ description: 'empty' });
      expect(wrapper.find('[data-testid=failure-strip]').exists()).toBe(false);
    });

    it('should name a failure in a strip above the rows an earlier load left, with a retry', async () => {
      const wrapper = mountTable(kind, { failure, rows: [kind.row(plainRow)] });

      expect(wrapper.find('[data-testid=failure-strip]').text()).toContain('backend down');
      await wrapper.find('[data-testid=failure-strip-retry]').trigger('click');

      expect(wrapper.emitted('retry')).toHaveLength(1);
    });

    it('should show no strip over an empty table, also beside the locked matching alert', () => {
      const wrapper = mountTable(kind, { failure, withAlert: true });

      expect(wrapper.find('[data-testid=alert-slot]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=failure-strip]').exists()).toBe(false);
    });
  });

  describe('rows', () => {
    it('should head the columns in this kind\'s words', () => {
      const cols: { label: string }[] = mountTable(kind).findComponent(RuiDataTable).props('cols');

      expect(cols.map(col => col.label)).toEqual(['common.datetime', 'common.type', kind.locationLabel, 'common.asset', 'asset_movement_matching.dialog.manual_action']);
    });

    it('should key each row by what the selection stores', () => {
      const wrapper = mountTable(kind, { rows: [kind.row(plainRow), kind.row(untrackedRow)] });

      expect(wrapper.findAll('[data-testid=row]').map(row => row.attributes('data-key'))).toEqual(['row-1', 'row-2']);
    });

    it('should show the row\'s type label, with the untracked badge only on an untracked row', () => {
      const wrapper = mountTable(kind, { rows: [kind.row(plainRow), kind.row(untrackedRow)] });

      expect(cell(wrapper, 'row-1', 'common.type').text()).toContain('Deposit');
      expect(cell(wrapper, 'row-1', 'common.type').find('[data-testid=unmatched-untracked-badge]').exists()).toBe(false);
      expect(cell(wrapper, 'row-2', 'common.type').text()).toContain('Withdrawal');
      expect(cell(wrapper, 'row-2', 'common.type').find('[data-testid=unmatched-untracked-badge]').text()).toContain('Untracked destination');
    });

    it('should highlight only the rows of the linked group', () => {
      const wrapper = mountTable(kind, {
        highlightedGroupIdentifier: kind.groupOf('row-2'),
        rows: [kind.row(plainRow), kind.row(untrackedRow)],
      });

      expect(wrapper.find('[data-key="row-1"]').classes()).not.toContain('bg-rui-warning/15!');
      expect(wrapper.find('[data-key="row-2"]').classes()).toContain('bg-rui-warning/15!');
    });

    it('should report a row action with the item the row stands for', async () => {
      const row = kind.row(plainRow);
      const wrapper = mountTable(kind, { rows: [row] });

      await cell(wrapper, 'row-1', 'asset_movement_matching.dialog.manual_action').find('[data-testid=row-action]').trigger('click');

      expect(wrapper.emitted('action')).toEqual([[{ action: 'ignore', item: row.original }]]);
    });
  });
});

describe('unmatched table, asset movement only', () => {
  const kind = MOVEMENT_KIND;

  it('should name a movement already resolved as external', () => {
    const wrapper = mountTable(kind, { rows: [movementRow(plainRow, { resolvedLabel: 'Resolved as income' })] });

    expect(cell(wrapper, 'row-1', 'common.type').find('[data-testid=unmatched-row-resolved]').text()).toBe('Resolved as income');
  });

  it('should mark a fiat movement in the asset cell', () => {
    const wrapper = mountTable(kind, { rows: [movementRow(plainRow, { isFiat: true })] });

    expect(cell(wrapper, 'row-1', 'common.asset').text()).toContain('asset_movement_matching.fiat_hint.label');
  });

  it('should show where an untracked withdrawal went, and nothing for a tracked one', () => {
    const wrapper = mountTable(kind, {
      rows: [
        movementRow(untrackedRow, { untrackedAddress: '0xA090e606E30bD747d4E6245a1517EbE430F0057e' }),
        movementRow(plainRow, { untrackedAddress: '0xA090e606E30bD747d4E6245a1517EbE430F0057e' }),
      ],
    });

    expect(cell(wrapper, 'row-2', 'common.type').findComponent({ name: 'HashLink' }).props('text')).toBe('0xA090e606E30bD747d4E6245a1517EbE430F0057e');
    expect(cell(wrapper, 'row-1', 'common.type').findComponent({ name: 'HashLink' }).exists()).toBe(false);
  });
});
