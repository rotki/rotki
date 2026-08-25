import type { MatchingFlow } from '@/modules/history/events/matching/types';
import type { UsePinnedMatchPanelOptions } from '@/modules/history/events/use-pinned-match-panel';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import MatchBridgeTransactionsPinned from '@/modules/history/events/MatchBridgeTransactionsPinned.vue';
import { PinnedNames } from '@/modules/session/types';

/**
 * The seam: the panel's behaviour lives in `usePinnedMatchPanel`, which has its own spec. What is
 * left here is the wiring that makes this the bridge panel rather than the asset movement one -
 * the bridge collections, the bridge flow, and the labels and explanation the drawer is given.
 */

const panel = {
  activeGroupIdentifier: ref<string | undefined>(),
  activePotentialMatchIdentifier: ref<number | undefined>(),
  clearHighlight: vi.fn().mockResolvedValue(undefined),
  closeDrawer: vi.fn().mockResolvedValue(undefined),
  modelSheetOpen: ref<boolean>(false),
  onMatched: vi.fn().mockResolvedValue(undefined),
  select: vi.fn(),
  showInHistoryEvents: vi.fn(),
  showPotentialMatchInHistoryEvents: vi.fn(),
  subject: ref<UnmatchedBridgeTransaction | undefined>(),
  unpin: vi.fn().mockResolvedValue(undefined),
};

let options: UsePinnedMatchPanelOptions<UnmatchedBridgeTransaction>;

vi.mock('@/modules/history/events/use-pinned-match-panel', () => ({
  usePinnedMatchPanel: (opts: UsePinnedMatchPanelOptions<UnmatchedBridgeTransaction>): unknown => {
    options = opts;
    return panel;
  },
}));

const unmatchedTransactions = ref<UnmatchedBridgeTransaction[]>([]);
const ignoredTransactions = ref<UnmatchedBridgeTransaction[]>([]);
const bridgeFlow = createMock<MatchingFlow>();
const entryLabels = ref({ locationHeader: 'Chain', type: 'Bridge transaction' });
const unmatchableExplanation = ref<string | undefined>('No counterpart is tracked.');

const flowSubjects: unknown[] = [];

vi.mock('@/modules/history/events/use-unmatched-bridge-transactions', () => ({
  useBridgeEntryLabels: (subject: unknown): unknown => {
    flowSubjects.push(subject);
    return entryLabels;
  },
  useBridgeMatchingFlow: (): MatchingFlow => bridgeFlow,
  useUnmatchedBridgeTransactions: (): Record<string, unknown> => ({ ignoredTransactions, unmatchedTransactions }),
}));

vi.mock('@/modules/history/events/use-untracked-bridge-counterpart', () => ({
  useBridgeUnmatchableExplanation: (subject: unknown): Record<string, unknown> => {
    flowSubjects.push(subject);
    return { unmatchableExplanation };
  },
}));

const ContentStub = defineComponent({
  emits: ['pin', 'select', 'show-in-events'],
  name: 'MatchBridgeTransactionsContent',
  props: {
    highlightedGroupIdentifier: { default: undefined, type: String },
    isPinned: { default: false, type: Boolean },
    onActionComplete: { default: undefined, type: Function },
  },
  setup: () => (): unknown => h('div', { 'data-testid': 'content' }),
});

const PotentialStub = defineComponent({
  emits: ['close', 'matched', 'show-in-events', 'show-unmatched-in-events'],
  name: 'PotentialMatchesContent',
  props: {
    emptyExplanation: { default: undefined, type: String },
    entryLabels: { default: undefined, type: Object },
    flow: { default: undefined, type: Object },
    highlightedIdentifier: { default: undefined, type: Number },
    isPinned: { default: false, type: Boolean },
    movement: { default: undefined, type: Object },
  },
  setup: () => (): unknown => h('div', { 'data-testid': 'potential' }),
});

const SheetStub = defineComponent({
  emits: ['update:modelValue'],
  name: 'PinnedDetailSheet',
  props: {
    label: { default: undefined, type: String },
    modelValue: { required: true, type: Boolean },
  },
  setup: (props, { slots }) => (): unknown => (props.modelValue
    ? h('div', { 'data-testid': 'sheet' }, [slots.header?.(), slots.default?.()])
    : null),
});

const transaction = createMock<UnmatchedBridgeTransaction>({ groupIdentifier: 'group-a', identifier: 11 });

describe('modules/history/events/MatchBridgeTransactionsPinned', () => {
  let wrapper: VueWrapper | undefined;

  function mountPanel(props: Record<string, unknown> = {}): VueWrapper {
    wrapper = mount(MatchBridgeTransactionsPinned, {
      global: {
        stubs: {
          MatchBridgeTransactionsContent: ContentStub,
          PinnedDetailSheet: SheetStub,
          PotentialMatchesContent: PotentialStub,
        },
      },
      props,
    });
    return wrapper;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    flowSubjects.length = 0;
    set(panel.activeGroupIdentifier, undefined);
    set(panel.activePotentialMatchIdentifier, undefined);
    set(panel.modelSheetOpen, false);
    set(panel.subject, undefined);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it('should drive the panel from the bridge transaction collections', () => {
    set(unmatchedTransactions, [transaction]);
    mountPanel();

    expect(options.pinnedName).toBe(PinnedNames.MATCH_BRIDGE_TRANSACTIONS);
    expect(options.sources).toStrictEqual([unmatchedTransactions, ignoredTransactions]);
  });

  it('should forward its highlight props to the panel', () => {
    mountPanel({
      highlightedGroupIdentifier: 'group-a',
      highlightedPotentialMatchIdentifier: 99,
      potentialMatchGroupIdentifier: 'group-c',
    });

    expect(options.highlightedGroupIdentifier()).toBe('group-a');
    expect(options.highlightedPotentialMatchIdentifier()).toBe(99);
    expect(options.potentialMatchGroupIdentifier()).toBe('group-c');
  });

  it('should name a transaction by its own identifier', () => {
    mountPanel();

    expect(options.getIdentifier(transaction)).toBe(11);
  });

  it('should derive the labels and the explanation from the selected transaction', () => {
    mountPanel();

    expect(flowSubjects).toHaveLength(2);
    for (const subject of flowSubjects)
      expect(subject).toBe(panel.subject);
  });

  it('should hand the content the highlighted group and the teardown', () => {
    set(panel.activeGroupIdentifier, 'group-a');
    const view = mountPanel();

    const content = view.findComponent(ContentStub);
    expect(content.props('highlightedGroupIdentifier')).toBe('group-a');
    expect(content.props('isPinned')).toBe(true);
    expect(content.props('onActionComplete')).toBe(panel.clearHighlight);
  });

  it('should report the content events to the panel', async () => {
    const view = mountPanel();
    const content = view.findComponent(ContentStub);

    content.vm.$emit('select', transaction);
    content.vm.$emit('show-in-events', transaction);
    content.vm.$emit('pin');
    await nextTick();

    expect(panel.select).toHaveBeenCalledWith(transaction);
    expect(panel.showInHistoryEvents).toHaveBeenCalledWith(transaction);
    expect(panel.unpin).toHaveBeenCalledTimes(1);
  });

  it('should keep the sheet closed while no transaction is selected', () => {
    const view = mountPanel();

    expect(view.find('[data-testid="sheet"]').exists()).toBe(false);
    expect(view.findComponent(PotentialStub).exists()).toBe(false);
  });

  it('should give the drawer the bridge flow, labels and explanation', async () => {
    const view = mountPanel();

    set(panel.modelSheetOpen, true);
    set(panel.subject, transaction);
    set(panel.activePotentialMatchIdentifier, 99);
    await nextTick();

    const potential = view.findComponent(PotentialStub);
    expect(potential.props('movement')).toBe(transaction);
    expect(potential.props('flow')).toBe(bridgeFlow);
    expect(potential.props('entryLabels')).toStrictEqual(get(entryLabels));
    expect(potential.props('emptyExplanation')).toBe('No counterpart is tracked.');
    expect(potential.props('highlightedIdentifier')).toBe(99);
    expect(potential.props('isPinned')).toBe(true);
  });

  it('should report the sheet events to the panel', async () => {
    const view = mountPanel();
    set(panel.modelSheetOpen, true);
    set(panel.subject, transaction);
    await nextTick();
    const potential = view.findComponent(PotentialStub);

    potential.vm.$emit('close');
    potential.vm.$emit('matched');
    potential.vm.$emit('show-in-events', { groupIdentifier: 'group-c', identifier: 99 });
    potential.vm.$emit('show-unmatched-in-events');
    await nextTick();

    expect(panel.closeDrawer).toHaveBeenCalledTimes(1);
    expect(panel.onMatched).toHaveBeenCalledTimes(1);
    expect(panel.showPotentialMatchInHistoryEvents)
      .toHaveBeenCalledWith({ groupIdentifier: 'group-c', identifier: 99 });
    expect(panel.showInHistoryEvents).toHaveBeenCalledWith(transaction);
  });

  it('should close the drawer from the sheet header', async () => {
    const view = mountPanel();
    set(panel.modelSheetOpen, true);
    set(panel.subject, transaction);
    await nextTick();

    await view.find('[data-testid="sheet"] button').trigger('click');

    expect(panel.closeDrawer).toHaveBeenCalledTimes(1);
  });
});
