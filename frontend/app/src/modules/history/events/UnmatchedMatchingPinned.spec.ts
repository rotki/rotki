import type { MatchingFlow, UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { UsePinnedMatchPanelOptions } from '@/modules/history/events/use-pinned-match-panel';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Component, defineComponent, h } from 'vue';
import MatchAssetMovementsPinned from '@/modules/history/events/MatchAssetMovementsPinned.vue';
import MatchBridgeTransactionsPinned from '@/modules/history/events/MatchBridgeTransactionsPinned.vue';
import { type PinnedName, PinnedNames } from '@/modules/session/types';

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
  subject: ref<UnmatchedEventGroup | undefined>(),
  unpin: vi.fn().mockResolvedValue(undefined),
};

let options: UsePinnedMatchPanelOptions<UnmatchedEventGroup>;

vi.mock('@/modules/history/events/use-pinned-match-panel', () => ({
  usePinnedMatchPanel: (opts: UsePinnedMatchPanelOptions<UnmatchedEventGroup>): unknown => {
    options = opts;
    return panel;
  },
}));

const unmatchedItems = ref<UnmatchedEventGroup[]>([]);
const ignoredItems = ref<UnmatchedEventGroup[]>([]);
/* Real objects, not `createMock`: the proxy is function-backed, so Vue's `type: Object` prop
   check rejects it on both `flow` and `movement`. */
const bridgeFlow: MatchingFlow = {
  getSuggestions: vi.fn().mockResolvedValue({ closeMatches: [], otherEvents: [] }),
  match: vi.fn().mockResolvedValue({ success: true }),
  refresh: vi.fn().mockResolvedValue(undefined),
};
const bridgeEntryLabels = ref({ locationHeader: 'Chain', type: 'Bridge transaction' });
const unmatchableExplanation = ref<string | undefined>('No counterpart is tracked.');

/** Every subject a label or explanation composable was handed, which must all be the panel's selection. */
const derivedFrom: unknown[] = [];

function explain(subject: unknown): Record<string, unknown> {
  derivedFrom.push(subject);
  return { unmatchableExplanation };
}

vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: (): Record<string, unknown> => ({ ignoredMovements: ignoredItems, unmatchedMovements: unmatchedItems }),
}));

vi.mock('@/modules/history/events/use-unmatched-bridge-transactions', () => ({
  useBridgeEntryLabels: (subject: unknown): unknown => {
    derivedFrom.push(subject);
    return bridgeEntryLabels;
  },
  useBridgeMatchingFlow: (): MatchingFlow => bridgeFlow,
  useUnmatchedBridgeTransactions: (): Record<string, unknown> => ({ ignoredTransactions: ignoredItems, unmatchedTransactions: unmatchedItems }),
}));

vi.mock('@/modules/history/events/use-untracked-movement-destination', () => ({ useMovementUnmatchableExplanation: explain }));

vi.mock('@/modules/history/events/use-untracked-bridge-counterpart', () => ({ useBridgeUnmatchableExplanation: explain }));

/** The kind-specific parts of a pinned matching panel that a spec over both kinds has to know. */
interface PinnedKind {
  name: string;
  pinned: Component;
  contentName: string;
  pinnedName: PinnedName;
  /** An item, and the identifier the matching endpoints know it by. */
  identified: { item: UnmatchedEventGroup; identifier: number };
  /** What the drawer hands the shared potential matches content, beyond the item itself. */
  drawer: { flow?: MatchingFlow; entryLabels?: Record<string, string> };
}

const PINNED_KINDS: PinnedKind[] = [
  {
    contentName: 'MatchBridgeTransactionsContent',
    drawer: { entryLabels: get(bridgeEntryLabels), flow: bridgeFlow },
    identified: { identifier: 11, item: { asset: 'ETH', events: [], groupIdentifier: 'group-a', identifier: 11 } },
    name: 'bridge',
    pinned: MatchBridgeTransactionsPinned,
    pinnedName: PinnedNames.MATCH_BRIDGE_TRANSACTIONS,
  },
  {
    contentName: 'MatchAssetMovementsContent',
    drawer: {},
    identified: {
      identifier: 77,
      item: createMock<UnmatchedEventGroup>({ events: [{ entry: { identifier: 77 } }], groupIdentifier: 'group-a' }),
    },
    name: 'asset movement',
    pinned: MatchAssetMovementsPinned,
    pinnedName: PinnedNames.MATCH_ASSET_MOVEMENTS,
  },
];

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

const selected: UnmatchedEventGroup = { asset: 'ETH', events: [], groupIdentifier: 'group-a', identifier: 11 };

describe.each(PINNED_KINDS)('unmatched matching pinned panel ($name)', (kind) => {
  const ContentStub = defineComponent({
    emits: ['pin', 'select', 'show-in-events'],
    name: kind.contentName,
    props: {
      highlightedGroupIdentifier: { default: undefined, type: String },
      isPinned: { default: false, type: Boolean },
      onActionComplete: { default: undefined, type: Function },
    },
    setup: () => (): unknown => h('div', { 'data-testid': 'content' }),
  });

  function mountPanel(props: Record<string, unknown> = {}): VueWrapper {
    return mount(kind.pinned, {
      global: {
        stubs: {
          PinnedDetailSheet: SheetStub,
          PotentialMatchesContent: PotentialStub,
          [kind.contentName]: ContentStub,
        },
      },
      props,
    });
  }

  async function openSheet(view: VueWrapper): Promise<void> {
    set(panel.modelSheetOpen, true);
    set(panel.subject, selected);
    await nextTick();
    expect(view.find('[data-testid="sheet"]').exists()).toBe(true);
  }

  beforeEach(() => {
    vi.clearAllMocks();
    derivedFrom.length = 0;
    set(panel.activeGroupIdentifier, undefined);
    set(panel.activePotentialMatchIdentifier, undefined);
    set(panel.modelSheetOpen, false);
    set(panel.subject, undefined);
  });

  it('should drive the panel from its own unmatched and ignored collections', () => {
    mountPanel();

    expect(options.pinnedName).toBe(kind.pinnedName);
    expect(options.sources).toStrictEqual([unmatchedItems, ignoredItems]);
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

  it('should name an item by the identifier the matching endpoints know it by', () => {
    mountPanel();

    expect(options.getIdentifier(kind.identified.item)).toBe(kind.identified.identifier);
  });

  it('should derive what the drawer explains from the selected item', () => {
    mountPanel();

    expect(derivedFrom.length).toBeGreaterThan(0);
    for (const subject of derivedFrom)
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

    content.vm.$emit('select', selected);
    content.vm.$emit('show-in-events', selected);
    content.vm.$emit('pin');
    await nextTick();

    expect(panel.select).toHaveBeenCalledWith(selected);
    expect(panel.showInHistoryEvents).toHaveBeenCalledWith(selected);
    expect(panel.unpin).toHaveBeenCalledTimes(1);
  });

  it('should keep the sheet closed while nothing is selected', () => {
    const view = mountPanel();

    expect(view.find('[data-testid="sheet"]').exists()).toBe(false);
    expect(view.findComponent(PotentialStub).exists()).toBe(false);
  });

  it('should give the drawer the selected item, its flow, labels and explanation', async () => {
    const view = mountPanel();
    set(panel.activePotentialMatchIdentifier, 99);
    await openSheet(view);

    const potential = view.findComponent(PotentialStub);
    expect(toRaw(potential.props('movement'))).toBe(selected);
    expect(potential.props('flow')).toBe(kind.drawer.flow);
    expect(potential.props('entryLabels')).toStrictEqual(kind.drawer.entryLabels);
    expect(potential.props('emptyExplanation')).toBe('No counterpart is tracked.');
    expect(potential.props('highlightedIdentifier')).toBe(99);
    expect(potential.props('isPinned')).toBe(true);
  });

  it('should report the sheet events to the panel', async () => {
    const view = mountPanel();
    await openSheet(view);
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
    expect(panel.showInHistoryEvents).toHaveBeenCalledWith(selected);
  });

  it('should close the drawer from the sheet header', async () => {
    const view = mountPanel();
    await openSheet(view);

    await view.find('[data-testid="sheet"] button').trigger('click');

    expect(panel.closeDrawer).toHaveBeenCalledTimes(1);
  });
});
