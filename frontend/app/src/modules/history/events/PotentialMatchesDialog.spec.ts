import type { UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import { FAKE_MATCHING_KIND_CASES, fakeMatchingKind } from '@test/utils/fake-matching-kind';
import { mountGeneric } from '@test/utils/mount-generic';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import PotentialMatchesDialog from '@/modules/history/events/PotentialMatchesDialog.vue';

const { pin, pinnedNames } = vi.hoisted(() => {
  const names: string[] = [];
  return { pin: vi.fn(), pinnedNames: names };
});

vi.mock('@/modules/shell/pinned/use-pinned-panel', () => ({
  usePinnedPanel: (name: string): { pin: typeof pin } => {
    pinnedNames.push(name);
    return { pin };
  },
}));

const ContentStub = defineComponent({
  emits: ['close', 'matched', 'show-in-events', 'show-unmatched-in-events'],
  name: 'PotentialMatchesContent',
  props: {
    emptyExplanation: { default: undefined, type: String },
    entryLabels: { default: undefined, type: Object },
    flow: { default: undefined, type: Object },
    movement: { default: undefined, type: Object },
  },
  setup: () => (): unknown => h('div'),
});

const stubs = {
  PotentialMatchesContent: ContentStub,
  RuiCard: { template: '<div><slot name="custom-header" /><slot /></div>' },
  RuiDialog: { template: '<div><slot /></div>' },
};

const item: UnmatchedEventGroup = { asset: 'ETH', events: [], groupIdentifier: 'group-a', identifier: 7 };

describe.each(FAKE_MATCHING_KIND_CASES)('potential matches dialog ($name kind)', (kindCase) => {
  let fake: ReturnType<typeof fakeMatchingKind>;

  function mountDialog(): ReturnType<typeof mountGeneric> {
    return mountGeneric(PotentialMatchesDialog, { item, kind: fake.kind, modelValue: true }, { stubs });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    pinnedNames.length = 0;
    fake = fakeMatchingKind(kindCase);
  });

  it('should give the content the item and its kind\'s flow, labels and explanation', () => {
    const content = mountDialog().findComponent(ContentStub);

    expect(toRaw(content.props('movement'))).toBe(item);
    expect(content.props('flow')).toBe(fake.flow);
    expect(content.props('entryLabels')).toStrictEqual(fake.entryLabels);
    expect(content.props('emptyExplanation')).toBe(fake.explanation);
  });

  it('should derive the labels and the explanation from the item', () => {
    mountDialog();

    expect(fake.subjects).toHaveLength(2);
    for (const subject of fake.subjects)
      expect(toRaw(subject())).toBe(item);
  });

  it('should pin its kind\'s tab on the item when asked to show it in events', async () => {
    const dialog = mountDialog();

    dialog.findComponent(ContentStub).vm.$emit('show-unmatched-in-events');
    await nextTick();

    expect(pinnedNames).toStrictEqual([kindCase.real.pinnedName]);
    expect(pin).toHaveBeenCalledExactlyOnceWith({ highlightedGroupIdentifier: 'group-a' });
    expect(dialog.emitted('update:modelValue')).toStrictEqual([[false]]);
    expect(dialog.emitted('pinned')).toHaveLength(1);
  });

  it('should pin the potential match next to the item', async () => {
    const dialog = mountDialog();

    dialog.findComponent(ContentStub).vm.$emit('show-in-events', { groupIdentifier: 'group-b', identifier: 9 });
    await nextTick();

    expect(pin).toHaveBeenCalledExactlyOnceWith({
      highlightedGroupIdentifier: 'group-a',
      highlightedPotentialMatchIdentifier: 9,
      potentialMatchGroupIdentifier: 'group-b',
    });
  });

  it('should close and report a match', async () => {
    const dialog = mountDialog();

    dialog.findComponent(ContentStub).vm.$emit('matched');
    await nextTick();

    expect(dialog.emitted('update:modelValue')).toStrictEqual([[false]]);
    expect(dialog.emitted('matched')).toHaveLength(1);
  });
});
