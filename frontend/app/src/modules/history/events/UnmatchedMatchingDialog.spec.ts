import type { UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import { FAKE_MATCHING_KIND_CASES, fakeMatchingKind } from '@test/utils/fake-matching-kind';
import { mountGeneric } from '@test/utils/mount-generic';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import UnmatchedMatchingDialog from '@/modules/history/events/UnmatchedMatchingDialog.vue';

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
  emits: ['close', 'pin', 'select', 'show-in-events'],
  name: 'UnmatchedMatchingContent',
  props: { kind: { default: undefined, type: Object } },
  setup: () => (): unknown => h('div'),
});

const stubs = {
  RuiCard: { template: '<div><slot name="custom-header" /><slot /></div>' },
  RuiDialog: { template: '<div><slot /></div>' },
  UnmatchedMatchingContent: ContentStub,
};

const item: UnmatchedEventGroup = { asset: 'ETH', events: [], groupIdentifier: 'group-a', identifier: 7 };

describe.each(FAKE_MATCHING_KIND_CASES)('unmatched matching dialog ($name kind)', (kindCase) => {
  let fake: ReturnType<typeof fakeMatchingKind>;

  function mountDialog(): ReturnType<typeof mountGeneric> {
    return mountGeneric(UnmatchedMatchingDialog, { kind: fake.kind, modelValue: true }, { stubs });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    pinnedNames.length = 0;
    fake = fakeMatchingKind(kindCase);
  });

  it('should title itself and hand the content its kind', () => {
    const dialog = mountDialog();

    expect(dialog.text()).toContain(kindCase.real.messages.title);
    expect(toRaw(dialog.findComponent(ContentStub).props('kind'))).toBe(fake.kind);
  });

  it('should ask its parent to find a match for the selected item', async () => {
    const dialog = mountDialog();

    dialog.findComponent(ContentStub).vm.$emit('select', item);
    await nextTick();

    expect(dialog.emitted('find-match')).toStrictEqual([[item]]);
  });

  it('should pin its kind\'s tab on the item it was asked to show, and close', async () => {
    const dialog = mountDialog();

    dialog.findComponent(ContentStub).vm.$emit('show-in-events', item);
    await nextTick();

    expect(pinnedNames).toStrictEqual([kindCase.real.pinnedName]);
    expect(pin).toHaveBeenCalledExactlyOnceWith({ highlightedGroupIdentifier: 'group-a' });
    expect(dialog.emitted('update:modelValue')).toStrictEqual([[false]]);
  });

  it('should pin the whole section without a highlight', async () => {
    const dialog = mountDialog();

    dialog.findComponent(ContentStub).vm.$emit('pin');
    await nextTick();

    expect(pin).toHaveBeenCalledExactlyOnceWith({});
  });
});
