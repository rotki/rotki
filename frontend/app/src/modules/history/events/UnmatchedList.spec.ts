import type { AnyMatchingKind } from '@test/utils/unmatched-panel-kinds';
import type { VueWrapper } from '@vue/test-utils';
import type { UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { UnmatchedFailure } from '@/modules/history/events/unmatched-actions';
import { mountGeneric } from '@test/utils/mount-generic';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, defineComponent } from 'vue';
import { assetMovementMatchingKind } from '@/modules/history/events/matching/asset-movement-matching-kind';
import { bridgeMatchingKind } from '@/modules/history/events/matching/bridge-matching-kind';
import UnmatchedList from '@/modules/history/events/UnmatchedList.vue';

const failure: UnmatchedFailure = { message: 'backend down', title: 'could not load' };

const rowsComposable = vi.hoisted(() => (options: { error?: () => unknown }): Record<string, unknown> => ({
  description: computed<string>(() => 'description'),
  emptyDescription: computed<string>(() => 'empty'),
  failure: computed<UnmatchedFailure | undefined>(() => (options.error?.() ? failure : undefined)),
  rows: computed<unknown[]>(() => []),
  specFor: vi.fn(),
}));

/** The match access both kinds' sources report, which the list turns into its alert. */
const access = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { isAutoMatchAllowed: ref<boolean>(true), minimumTier: ref<string | null>(null) };
});

function source(): Record<string, unknown> {
  return { autoMatchMinimumTier: access.minimumTier, isAutoMatchAllowed: access.isAutoMatchAllowed };
}

vi.mock('@/modules/history/events/use-unmatched-bridge-rows', () => ({ useUnmatchedBridgeRows: rowsComposable }));
vi.mock('@/modules/history/events/use-unmatched-movement-rows', () => ({ useUnmatchedMovementRows: rowsComposable }));
vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({ useUnmatchedAssetMovements: source }));
vi.mock('@/modules/history/events/use-unmatched-bridge-transactions', async importOriginal => ({
  ...await importOriginal<Record<string, unknown>>(),
  useUnmatchedBridgeTransactions: source,
}));

interface ListProps {
  error?: unknown;
  isPinned?: boolean;
  showRestore?: boolean;
  /** How many items the list is given; only the count is read. */
  itemCount?: number;
}

function presentation(name: string, extraProps: string[] = []): ReturnType<typeof defineComponent> {
  return defineComponent({
    name,
    props: ['failure', 'rows', 'emptyDescription', ...extraProps],
    emits: ['action', 'retry'],
    template: '<div><slot name="alert" /></div>',
  });
}

const AlertStub = defineComponent({
  name: 'UnmatchedMatchDisabledAlert',
  props: ['variant', 'count', 'matchMinimumTier'],
  template: '<div />',
});

const global = {
  provide: libraryDefaults,
  stubs: {
    UnmatchedCards: presentation('UnmatchedCards'),
    UnmatchedMatchDisabledAlert: AlertStub,
    UnmatchedTable: presentation('UnmatchedTable', ['variant']),
  },
};

const LIST_KINDS: { name: string; kind: AnyMatchingKind }[] = [
  { kind: bridgeMatchingKind, name: 'bridge' },
  { kind: assetMovementMatchingKind, name: 'asset movement' },
];

describe.each(LIST_KINDS)('unmatched list ($name)', ({ kind }) => {
  function mountList({ itemCount = 0, ...props }: ListProps = {}): VueWrapper {
    const items: UnmatchedEventGroup[] = Array.from({ length: itemCount }, (_, index) => ({
      asset: 'ETH',
      events: [],
      groupIdentifier: `group-${index}`,
    }));
    return mountGeneric(UnmatchedList, { ...props, items, kind, selected: [] }, global);
  }

  beforeEach(() => {
    set(access.isAutoMatchAllowed, true);
    set(access.minimumTier, null);
  });

  it('should render the table with its variant in the dialog', () => {
    const wrapper = mountList();

    expect(wrapper.findComponent({ name: 'UnmatchedTable' }).props('variant')).toBe(kind.variant);
    expect(wrapper.findComponent({ name: 'UnmatchedCards' }).exists()).toBe(false);
  });

  it('should render the cards without a variant attribute when pinned', () => {
    const wrapper = mountList({ isPinned: true });
    const cards = wrapper.findComponent({ name: 'UnmatchedCards' });

    expect(cards.exists()).toBe(true);
    expect(cards.attributes()).not.toHaveProperty('variant');
  });

  it('should hand the failure to the dialog table', () => {
    const wrapper = mountList({ error: new Error('backend down') });

    expect(wrapper.findComponent({ name: 'UnmatchedTable' }).props('failure')).toEqual(failure);
  });

  it('should hand the failure to the pinned cards', () => {
    const wrapper = mountList({ error: new Error('backend down'), isPinned: true });

    expect(wrapper.findComponent({ name: 'UnmatchedCards' }).props('failure')).toEqual(failure);
  });

  it('should hand no failure while nothing failed', () => {
    const wrapper = mountList();

    expect(wrapper.findComponent({ name: 'UnmatchedTable' }).props('failure')).toBeUndefined();
  });

  it('should pass a retry and an action from the presentation up to its host', () => {
    const wrapper = mountList({ error: new Error('backend down') });
    const table = wrapper.findComponent({ name: 'UnmatchedTable' });
    const payload = { action: 'ignore', item: {} };

    table.vm.$emit('retry');
    table.vm.$emit('action', payload);

    expect(wrapper.emitted('retry')).toHaveLength(1);
    expect(wrapper.emitted('action')).toEqual([[payload]]);
  });

  it('should offer pinning only in the dialog', async () => {
    const dialog = mountList();
    await dialog.find('button').trigger('click');

    expect(dialog.emitted('pin')).toHaveLength(1);
    expect(mountList({ isPinned: true }).find('button').exists()).toBe(false);
  });

  it('should show no match alert while matching is allowed', () => {
    expect(mountList().findComponent(AlertStub).exists()).toBe(false);
  });

  it('should count the unmatched items in the match alert', () => {
    set(access.isAutoMatchAllowed, false);
    set(access.minimumTier, 'basic');
    const wrapper = mountList({ itemCount: 2 });
    const alert = wrapper.findComponent(AlertStub);

    expect(alert.props()).toEqual({ count: 2, matchMinimumTier: 'basic', variant: kind.variant });
  });

  it('should count nothing in the match alert of the ignored tab', () => {
    set(access.isAutoMatchAllowed, false);
    const wrapper = mountList({ itemCount: 2, showRestore: true });

    expect(wrapper.findComponent(AlertStub).props('count')).toBe(0);
  });
});
