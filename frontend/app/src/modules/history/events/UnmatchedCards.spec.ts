import type { UnmatchedRowActionSpec } from '@/modules/history/events/unmatched-actions';
import { createMock } from '@test/utils/create-mock';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { movementRow, UNMATCHED_PANEL_KINDS, type UnmatchedPanelKind, type UnmatchedRowCase } from '@test/utils/unmatched-panel-kinds';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { type Component, defineComponent } from 'vue';
import UnmatchedBridgesCards from '@/modules/history/events/UnmatchedBridgesCards.vue';
import UnmatchedMovementsCards from '@/modules/history/events/UnmatchedMovementsCards.vue';
import '@test/i18n';

const UnmatchedActions = defineComponent({
  name: 'UnmatchedActions',
  props: ['spec'],
  emits: ['action'],
  template: '<button data-testid="card-action" @click.stop="$emit(\'action\', \'ignore\')" />',
});

const COMPONENTS: Record<UnmatchedPanelKind['name'], Component> = {
  'asset movement': UnmatchedMovementsCards,
  'bridge': UnmatchedBridgesCards,
};

const plainRow: UnmatchedRowCase = { key: 'row-1', typeLabel: 'Deposit' };

const untrackedRow: UnmatchedRowCase = {
  key: 'row-2',
  typeLabel: 'Withdrawal',
  untracked: { label: 'Untracked destination', tooltip: 'Not one of your accounts' },
};

function mountCards(kind: UnmatchedPanelKind, rows: unknown[]): VueWrapper {
  return mount(COMPONENTS[kind.name], {
    global: {
      provide: libraryDefaults,
      stubs: { DateDisplay: true, HashLink: true, HistoryEventAsset: true, LocationDisplay: true, UnmatchedActions },
    },
    props: {
      emptyDescription: 'empty',
      rows,
      selected: [],
      specFor: () => createMock<UnmatchedRowActionSpec>(),
    },
  });
}

function card(wrapper: VueWrapper, index: number): ReturnType<VueWrapper['findAll']>[number] {
  return wrapper.findAll('[data-testid=unmatched-card]')[index];
}

describe.each(UNMATCHED_PANEL_KINDS)('unmatched cards, $name', (kind) => {
  it('should head each card with the row\'s type label', () => {
    const wrapper = mountCards(kind, [kind.row(plainRow), kind.row(untrackedRow)]);

    expect(card(wrapper, 0).text()).toContain('Deposit');
    expect(card(wrapper, 1).text()).toContain('Withdrawal');
  });

  it('should explain an untracked row in this kind\'s words, and leave a tracked one alone', () => {
    const wrapper = mountCards(kind, [kind.row(plainRow), kind.row(untrackedRow)]);

    expect(card(wrapper, 0).find('[data-testid=unmatched-card-untracked-reason]').exists()).toBe(false);
    expect(card(wrapper, 1).find('[data-testid=unmatched-card-untracked-reason] i18n-t-stub').attributes('keypath')).toBe(kind.untrackedReasonKey);
  });

  it('should select a card by what the selection stores', async () => {
    const wrapper = mountCards(kind, [kind.row(plainRow)]);

    await card(wrapper, 0).trigger('click');

    expect(wrapper.emitted('update:selected')).toEqual([[['row-1']]]);
  });

  it('should report a card action with the item the card stands for', async () => {
    const row = kind.row(plainRow);
    const wrapper = mountCards(kind, [row]);

    await card(wrapper, 0).find('[data-testid=card-action]').trigger('click');

    expect(wrapper.emitted('action')).toEqual([[{ action: 'ignore', item: row.original }]]);
  });
});

describe('unmatched cards, asset movement only', () => {
  const kind = UNMATCHED_PANEL_KINDS[1];

  it('should name a movement already resolved as external', () => {
    const wrapper = mountCards(kind, [movementRow(plainRow, { resolvedAsExternal: true, resolvedLabel: 'Resolved as income' })]);

    expect(card(wrapper, 0).find('[data-testid=unmatched-row-resolved]').text()).toBe('Resolved as income');
  });

  it('should mark a fiat movement', () => {
    const wrapper = mountCards(kind, [movementRow(plainRow, { isFiat: true }), movementRow(untrackedRow)]);

    expect(card(wrapper, 0).text()).toContain('asset_movement_matching.fiat_hint.label');
    expect(card(wrapper, 1).text()).not.toContain('asset_movement_matching.fiat_hint.label');
  });

  it('should show where an untracked withdrawal went', () => {
    const wrapper = mountCards(kind, [movementRow(untrackedRow, { destinationAddress: '0xA090e606E30bD747d4E6245a1517EbE430F0057e' })]);

    expect(card(wrapper, 0).findComponent({ name: 'HashLink' }).props('text')).toBe('0xA090e606E30bD747d4E6245a1517EbE430F0057e');
  });
});
