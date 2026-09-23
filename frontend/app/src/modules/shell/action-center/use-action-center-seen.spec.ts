import type { EffectScope } from 'vue';
import { afterEach, assert, beforeEach, describe, expect, it } from 'vitest';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { type ActionItem, type ActionTarget, ActionUrgency, createActionItem } from '@/modules/core/action-center/types';
import { useActionCenterSeen } from '@/modules/shell/action-center/use-action-center-seen';

function row(id: string, count: number, overrides: Partial<ActionItem> = {}): ActionItem {
  return {
    ...createActionItem<ActionTarget, string>({
      actionLabel: 'act',
      count,
      description: 'description',
      icon: 'lu-key-round',
      id,
      target: { kind: 'route', to: { name: '/accounts/' } },
      title: id,
      urgency: ActionUrgency.DECISION,
    }),
    ...overrides,
  };
}

const items = ref<ActionItem[]>([]);
const checking = ref<boolean>(false);
const active = computed<ActionItem[]>(() => get(items).filter(item => !item.loading && item.count > 0));

let scope: EffectScope | undefined;

function seen(): ReturnType<typeof useActionCenterSeen> {
  scope = effectScope();
  const result = scope.run(() => useActionCenterSeen({ active, checking, items }));
  assert(result);
  return result;
}

describe('modules/shell/action-center/use-action-center-seen', () => {
  beforeEach(() => {
    localStorage.clear();
    set(useLoggedUserIdentifier(), 'alice');
    set(items, []);
    set(checking, false);
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should count every active row as new before the user has looked', () => {
    set(items, [row('a', 2), row('b', 1), row('cleared', 0)]);
    const { newIds } = seen();

    expect(get(newIds)).toEqual(['a', 'b']);
  });

  it('should count a row as new again once it grows past what was seen, and a row that was not there', async () => {
    set(items, [row('a', 2)]);
    const { markSeen, newIds } = seen();
    markSeen();
    expect(get(newIds)).toEqual([]);

    set(items, [row('a', 3), row('b', 1)]);
    await nextTick();

    expect(get(newIds)).toEqual(['a', 'b']);
  });

  it('should forget nothing when closed before the first scan, while every count still reads zero', async () => {
    set(items, [row('a', 2)]);
    const { markSeen, newIds } = seen();
    markSeen();

    set(checking, true);
    set(items, [row('a', 0)]);
    await nextTick();
    markSeen();

    set(checking, false);
    set(items, [row('a', 2)]);
    await nextTick();

    expect(get(newIds)).toEqual([]);
  });

  it('should keep what was seen when closed mid-scan on a count that has not caught up yet', async () => {
    set(items, [row('a', 5)]);
    const { markSeen, newIds } = seen();
    markSeen();

    set(checking, true);
    set(items, [row('a', 2)]);
    await nextTick();
    markSeen();

    set(items, [row('a', 5)]);
    set(checking, false);
    await nextTick();

    expect(get(newIds)).toEqual([]);
  });

  it('should lower what was seen when a count drops, so rows that come back later are new', async () => {
    set(items, [row('a', 5)]);
    const { markSeen, newIds } = seen();
    markSeen();

    set(items, [row('a', 2)]);
    await nextTick();
    set(items, [row('a', 3)]);
    await nextTick();

    expect(get(newIds)).toEqual(['a']);
  });

  it('should not lower what was seen from a row that is still loading', async () => {
    set(items, [row('a', 5)]);
    const { markSeen, newIds } = seen();
    markSeen();

    set(items, [row('a', 0, { loading: true })]);
    await nextTick();
    set(items, [row('a', 5)]);
    await nextTick();

    expect(get(newIds)).toEqual([]);
  });

  it('should keep what each user has seen apart', async () => {
    set(items, [row('a', 1)]);
    const { markSeen, newIds } = seen();
    markSeen();
    expect(get(newIds)).toEqual([]);
    // storage writes flush before render, so the next user's key must not change in the same tick
    await nextTick();

    set(useLoggedUserIdentifier(), 'bob');
    await nextTick();

    expect(get(newIds)).toEqual(['a']);
  });
});
