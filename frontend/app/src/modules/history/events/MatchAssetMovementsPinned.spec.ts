import type { UsePinnedMatchPanelOptions } from '@/modules/history/events/use-pinned-match-panel';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import MatchAssetMovementsPinned from '@/modules/history/events/MatchAssetMovementsPinned.vue';
import { PinnedNames } from '@/modules/session/types';

/**
 * The seam: the panel's decisions live in `usePinnedMatchPanel`, which has its own spec. Covered
 * here is the wiring only — which rows the panel searches, how a row names its event, and that the
 * content components receive the panel's state and report their events back.
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
  subject: ref<UnmatchedAssetMovement | undefined>(),
  unpin: vi.fn().mockResolvedValue(undefined),
};

let options: UsePinnedMatchPanelOptions<UnmatchedAssetMovement>;

vi.mock('@/modules/history/events/use-pinned-match-panel', () => ({
  usePinnedMatchPanel: (opts: UsePinnedMatchPanelOptions<UnmatchedAssetMovement>): unknown => {
    options = opts;
    return panel;
  },
}));

const unmatchedMovements = ref<UnmatchedAssetMovement[]>([]);
const ignoredMovements = ref<UnmatchedAssetMovement[]>([]);

vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: (): Record<string, unknown> => ({ ignoredMovements, unmatchedMovements }),
}));

const ContentStub = defineComponent({
  emits: ['pin', 'select', 'show-in-events'],
  name: 'MatchAssetMovementsContent',
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

const movement = createMock<UnmatchedAssetMovement>({ groupIdentifier: 'group-a' });

describe('modules/history/events/MatchAssetMovementsPinned', () => {
  let wrapper: VueWrapper | undefined;

  function mountPanel(props: Record<string, unknown> = {}): VueWrapper {
    wrapper = mount(MatchAssetMovementsPinned, {
      global: {
        stubs: {
          MatchAssetMovementsContent: ContentStub,
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
    set(panel.activeGroupIdentifier, undefined);
    set(panel.activePotentialMatchIdentifier, undefined);
    set(panel.modelSheetOpen, false);
    set(panel.subject, undefined);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it('should drive the panel from the asset movement collections', () => {
    set(unmatchedMovements, [movement]);
    set(ignoredMovements, []);
    mountPanel();

    expect(options.pinnedName).toBe(PinnedNames.MATCH_ASSET_MOVEMENTS);
    expect(options.sources).toStrictEqual([unmatchedMovements, ignoredMovements]);
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

  it('should name a movement by the event inside its collection', () => {
    mountPanel();

    const identifier = options.getIdentifier(createMock<UnmatchedAssetMovement>({
      events: [{ entry: { identifier: 77 } }],
      groupIdentifier: 'group-a',
    }));

    expect(identifier).toBe(77);
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

    content.vm.$emit('select', movement);
    content.vm.$emit('show-in-events', movement);
    content.vm.$emit('pin');
    await nextTick();

    expect(panel.select).toHaveBeenCalledWith(movement);
    expect(panel.showInHistoryEvents).toHaveBeenCalledWith(movement);
    expect(panel.unpin).toHaveBeenCalledTimes(1);
  });

  it('should keep the sheet closed while no movement is selected', () => {
    const view = mountPanel();

    expect(view.find('[data-testid="sheet"]').exists()).toBe(false);
    expect(view.findComponent(PotentialStub).exists()).toBe(false);
  });

  it('should show the selected movement once the sheet opens', async () => {
    const view = mountPanel();

    set(panel.modelSheetOpen, true);
    set(panel.subject, movement);
    set(panel.activePotentialMatchIdentifier, 99);
    await nextTick();

    const potential = view.findComponent(PotentialStub);
    expect(potential.props('movement')).toBe(movement);
    expect(potential.props('highlightedIdentifier')).toBe(99);
    expect(potential.props('isPinned')).toBe(true);
  });

  it('should report the sheet events to the panel', async () => {
    const view = mountPanel();
    set(panel.modelSheetOpen, true);
    set(panel.subject, movement);
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
    expect(panel.showInHistoryEvents).toHaveBeenCalledWith(movement);
  });

  it('should close the drawer from the sheet header', async () => {
    const view = mountPanel();
    set(panel.modelSheetOpen, true);
    set(panel.subject, movement);
    await nextTick();

    await view.find('[data-testid="sheet"] button').trigger('click');

    expect(panel.closeDrawer).toHaveBeenCalledTimes(1);
  });
});
