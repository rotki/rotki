import type { EffectScope } from 'vue';
import { afterEach, assert, beforeEach, describe, expect, it } from 'vitest';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { useActionCenterFolds } from '@/modules/shell/action-center/use-action-center-folds';

let scope: EffectScope | undefined;

function folds(): ReturnType<typeof useActionCenterFolds> {
  scope = effectScope();
  const result = scope.run(() => useActionCenterFolds());
  assert(result);
  return result;
}

describe('modules/shell/action-center/use-action-center-folds', () => {
  beforeEach(() => {
    localStorage.clear();
    set(useLoggedUserIdentifier(), 'alice');
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should start with nothing folded', () => {
    expect(get(folds().modelFolded)).toEqual([]);
  });

  it('should remember the folded sections across a new mount', async () => {
    set(folds().modelFolded, ['history']);
    await nextTick();
    scope?.stop();

    expect(get(folds().modelFolded)).toEqual(['history']);
  });

  it('should keep each user\'s folds apart', async () => {
    const { modelFolded } = folds();
    set(modelFolded, ['history']);
    await nextTick();

    set(useLoggedUserIdentifier(), 'bob');
    await nextTick();

    expect(get(modelFolded)).toEqual([]);
  });
});
