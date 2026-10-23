import type { UnmatchedFailure } from '@/modules/history/events/unmatched-actions';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { computed, defineComponent } from 'vue';
import UnmatchedMovementsList from '@/modules/history/events/UnmatchedMovementsList.vue';

const failure: UnmatchedFailure = { message: 'backend down', title: 'could not load' };

vi.mock('@/modules/history/events/use-unmatched-movement-rows', () => ({
  useUnmatchedMovementRows: (options: { error?: () => unknown }): Record<string, unknown> => ({
    description: computed<string>(() => 'description'),
    emptyDescription: computed<string>(() => 'empty'),
    failure: computed<UnmatchedFailure | undefined>(() => (options.error?.() ? failure : undefined)),
    rows: computed<unknown[]>(() => []),
    specFor: vi.fn(),
  }),
}));

function presentation(name: string): ReturnType<typeof defineComponent> {
  return defineComponent({
    name,
    props: ['failure'],
    emits: ['retry'],
    template: '<div />',
  });
}

function mountList(props: { error?: unknown; isPinned?: boolean } = {}): VueWrapper {
  return mount(UnmatchedMovementsList, {
    global: {
      provide: libraryDefaults,
      stubs: {
        UnmatchedMovementsCards: presentation('UnmatchedMovementsCards'),
        UnmatchedMovementsTable: presentation('UnmatchedMovementsTable'),
      },
    },
    props: { ...props, movements: [], selected: [] },
  });
}

describe('unmatchedMovementsList', () => {
  it('should hand the failure to the dialog table', () => {
    const wrapper = mountList({ error: new Error('backend down') });

    expect(wrapper.findComponent({ name: 'UnmatchedMovementsTable' }).props('failure')).toEqual(failure);
  });

  it('should hand the failure to the pinned cards', () => {
    const wrapper = mountList({ error: new Error('backend down'), isPinned: true });

    expect(wrapper.findComponent({ name: 'UnmatchedMovementsCards' }).props('failure')).toEqual(failure);
  });

  it('should hand no failure while nothing failed', () => {
    const wrapper = mountList();

    expect(wrapper.findComponent({ name: 'UnmatchedMovementsTable' }).props('failure')).toBeUndefined();
  });

  it('should pass a retry from the presentation up to its host', async () => {
    const wrapper = mountList({ error: new Error('backend down') });

    wrapper.findComponent({ name: 'UnmatchedMovementsTable' }).vm.$emit('retry');

    expect(wrapper.emitted('retry')).toHaveLength(1);
  });
});
