import type { EffectScope } from 'vue';
import { afterEach, assert, beforeEach, describe, expect, it } from 'vitest';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { type ActionItem, type ActionTarget, ActionUrgency, createActionItem } from '@/modules/core/action-center/types';
import { useActionCenterProgress } from '@/modules/shell/action-center/use-action-center-progress';

function row(id: string, count: number): ActionItem {
  return createActionItem<ActionTarget, string>({
    actionLabel: 'act',
    count,
    description: 'description',
    icon: 'lu-key-round',
    id,
    target: { kind: 'route', to: { name: '/accounts/' } },
    title: id,
    urgency: ActionUrgency.DECISION,
  });
}

const items = ref<ActionItem[]>([]);
const checking = ref<boolean>(false);

let scope: EffectScope | undefined;

function progress(): ReturnType<typeof useActionCenterProgress> {
  scope = effectScope();
  const result = scope.run(() => useActionCenterProgress({ checking, items }));
  assert(result);
  return result;
}

describe('modules/shell/action-center/use-action-center-progress', () => {
  beforeEach(() => {
    localStorage.clear();
    set(useLoggedUserIdentifier(), 'alice');
    set(items, []);
    set(checking, false);
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should show nothing before the user has ever closed the center', () => {
    set(items, [row('duplicates', 12)]);

    expect(get(progress().previousCounts)).toEqual({});
  });

  it('should report the rows that went down or cleared since the center was last closed', () => {
    set(items, [row('duplicates', 40), row('conflicts', 2), row('prices', 3)]);
    const { markClosed, previousCounts } = progress();
    markClosed();

    set(items, [row('duplicates', 12), row('conflicts', 0), row('prices', 5)]);

    expect(get(previousCounts)).toEqual({ conflicts: 2, duplicates: 40 });
  });

  it('should compare with the latest close, not an older one', () => {
    set(items, [row('duplicates', 40)]);
    const { markClosed, previousCounts } = progress();
    markClosed();
    set(items, [row('duplicates', 12)]);
    markClosed();

    set(items, [row('duplicates', 10)]);

    expect(get(previousCounts)).toEqual({ duplicates: 12 });
  });

  it('should keep the comparison across sessions, per user', async () => {
    set(items, [row('duplicates', 40)]);
    progress().markClosed();
    await nextTick();
    scope?.stop();

    set(items, [row('duplicates', 12)]);
    expect(get(progress().previousCounts)).toEqual({ duplicates: 40 });
    scope?.stop();

    set(useLoggedUserIdentifier(), 'bob');
    expect(get(progress().previousCounts)).toEqual({});
  });

  it('should neither compare nor remember before the first scan, when every count reads zero', () => {
    set(items, [row('duplicates', 40)]);
    const { markClosed, previousCounts } = progress();
    markClosed();

    set(checking, true);
    set(items, [row('duplicates', 0)]);

    expect(get(previousCounts)).toEqual({});

    markClosed();
    set(checking, false);
    set(items, [row('duplicates', 12)]);

    expect(get(previousCounts)).toEqual({ duplicates: 40 });
  });
});
