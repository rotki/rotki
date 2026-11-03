import type { UnmatchedRowActionSpec } from '@/modules/history/events/unmatched-actions';
import type { UnmatchedRow } from '@/modules/history/events/unmatched-row';
import { createMock } from '@test/utils/create-mock';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { MOVEMENT_KIND, movementRow, plainRow, UNMATCHED_PANEL_KINDS, UnmatchedActionsStub, type UnmatchedPanelKind, untrackedRow } from '@test/utils/unmatched-panel-kinds';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import UnmatchedCards from '@/modules/history/events/UnmatchedCards.vue';
import '@test/i18n';

function mountCards(kind: UnmatchedPanelKind, rows: UnmatchedRow<unknown>[]): VueWrapper {
  return mount(UnmatchedCards, {
    global: {
      provide: libraryDefaults,
      stubs: { DateDisplay: true, HashLink: true, HistoryEventAsset: true, LocationDisplay: true, UnmatchedActions: UnmatchedActionsStub },
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

  it('should explain an untracked row, and leave a tracked one alone', () => {
    const wrapper = mountCards(kind, [kind.row(plainRow), kind.row(untrackedRow)]);

    expect(card(wrapper, 0).find('[data-testid=unmatched-card-untracked-reason]').exists()).toBe(false);
    expect(card(wrapper, 1).find('[data-testid=unmatched-card-untracked-reason] i18n-t-stub').attributes('keypath')).toBe('asset_movement_matching.dialog.untracked_reason');
  });

  it('should select a card by what the selection stores', async () => {
    const wrapper = mountCards(kind, [kind.row(plainRow)]);

    await card(wrapper, 0).trigger('click');

    expect(wrapper.emitted('update:selected')).toEqual([[['row-1']]]);
  });

  it('should report a card action with the item the card stands for', async () => {
    const row = kind.row(plainRow);
    const wrapper = mountCards(kind, [row]);

    await card(wrapper, 0).find('[data-testid=row-action]').trigger('click');

    expect(wrapper.emitted('action')).toEqual([[{ action: 'ignore', item: row.original }]]);
  });
});

describe('unmatched cards, asset movement only', () => {
  const kind = MOVEMENT_KIND;

  it('should name a movement already resolved as external', () => {
    const wrapper = mountCards(kind, [movementRow(plainRow, { resolvedLabel: 'Resolved as income' })]);

    expect(card(wrapper, 0).find('[data-testid=unmatched-row-resolved]').text()).toBe('Resolved as income');
  });

  it('should mark a fiat movement', () => {
    const wrapper = mountCards(kind, [movementRow(plainRow, { isFiat: true }), movementRow(untrackedRow)]);

    expect(card(wrapper, 0).text()).toContain('asset_movement_matching.fiat_hint.label');
    expect(card(wrapper, 1).text()).not.toContain('asset_movement_matching.fiat_hint.label');
  });

  it('should show where an untracked withdrawal went', () => {
    const wrapper = mountCards(kind, [movementRow(untrackedRow, { untrackedAddress: '0xA090e606E30bD747d4E6245a1517EbE430F0057e' })]);

    expect(card(wrapper, 0).findComponent({ name: 'HashLink' }).props('text')).toBe('0xA090e606E30bD747d4E6245a1517EbE430F0057e');
  });
});
