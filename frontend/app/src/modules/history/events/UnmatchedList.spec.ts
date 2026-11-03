import type { UnmatchedFailure, UnmatchedMatchAccess } from '@/modules/history/events/unmatched-actions';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { createMock } from '@test/utils/create-mock';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { computed, defineComponent } from 'vue';
import { UnmatchedVariant } from '@/modules/history/events/unmatched-row';
import UnmatchedBridgesList from '@/modules/history/events/UnmatchedBridgesList.vue';
import UnmatchedMovementsList from '@/modules/history/events/UnmatchedMovementsList.vue';

const failure: UnmatchedFailure = { message: 'backend down', title: 'could not load' };

const rowsComposable = vi.hoisted(() => (options: { error?: () => unknown }): Record<string, unknown> => ({
  description: computed<string>(() => 'description'),
  emptyDescription: computed<string>(() => 'empty'),
  failure: computed<UnmatchedFailure | undefined>(() => (options.error?.() ? failure : undefined)),
  rows: computed<unknown[]>(() => []),
  specFor: vi.fn(),
}));

vi.mock('@/modules/history/events/use-unmatched-bridge-rows', () => ({ useUnmatchedBridgeRows: rowsComposable }));
vi.mock('@/modules/history/events/use-unmatched-movement-rows', () => ({ useUnmatchedMovementRows: rowsComposable }));

interface ListProps {
  error?: unknown;
  isPinned?: boolean;
  matchAccess?: UnmatchedMatchAccess;
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

interface ListKind {
  name: string;
  variant: UnmatchedVariant;
  mount: (props: ListProps) => VueWrapper;
}

const LIST_KINDS: ListKind[] = [
  {
    mount: ({ itemCount = 0, ...props }): VueWrapper => mount(UnmatchedBridgesList, {
      global,
      props: { ...props, selected: [], transactions: Array.from({ length: itemCount }, () => createMock<UnmatchedBridgeTransaction>()) },
    }),
    name: 'bridge',
    variant: UnmatchedVariant.BRIDGE,
  },
  {
    mount: ({ itemCount = 0, ...props }): VueWrapper => mount(UnmatchedMovementsList, {
      global,
      props: { ...props, movements: Array.from({ length: itemCount }, () => createMock<UnmatchedAssetMovement>()), selected: [] },
    }),
    name: 'asset movement',
    variant: UnmatchedVariant.ASSET_MOVEMENT,
  },
];

describe.each(LIST_KINDS)('unmatched list ($name)', (kind) => {
  function mountList(props: ListProps = {}): VueWrapper {
    return kind.mount(props);
  }

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

  it('should show no match alert while matching is allowed or not gated', () => {
    expect(mountList().findComponent(AlertStub).exists()).toBe(false);
    expect(mountList({ matchAccess: { allowed: true, minimumTier: null } }).findComponent(AlertStub).exists()).toBe(false);
  });

  it('should count the unmatched items in the match alert', () => {
    const wrapper = mountList({ itemCount: 2, matchAccess: { allowed: false, minimumTier: 'basic' } });
    const alert = wrapper.findComponent(AlertStub);

    expect(alert.props()).toEqual({ count: 2, matchMinimumTier: 'basic', variant: kind.variant });
  });

  it('should count nothing in the match alert of the ignored tab', () => {
    const wrapper = mountList({ itemCount: 2, matchAccess: { allowed: false, minimumTier: null }, showRestore: true });

    expect(wrapper.findComponent(AlertStub).props('count')).toBe(0);
  });
});
