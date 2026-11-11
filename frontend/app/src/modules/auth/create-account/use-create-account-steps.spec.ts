import type { CreateAccountMode } from '@/modules/auth/create-account/types';
import { describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { stepPosition, useCreateAccountSteps } from '@/modules/auth/create-account/use-create-account-steps';
import '@test/i18n';

function createSteps(mode?: CreateAccountMode, step: number = 1): ReturnType<typeof useCreateAccountSteps> {
  return useCreateAccountSteps(ref<CreateAccountMode | undefined>(mode), ref<number>(step));
}

describe('useCreateAccountSteps', () => {
  it('should list no steps while the path is still being chosen', () => {
    const { current, steps } = createSteps();

    expect(get(steps)).toStrictEqual([]);
    expect(get(current)).toBeUndefined();
  });

  it('should give the create path its profile and preferences steps', () => {
    expect(get(createSteps('create').steps).map(step => step.id)).toStrictEqual(['profile', 'preferences']);
  });

  it('should give the restore path its premium, profile and summary steps', () => {
    expect(get(createSteps('restore').steps).map(step => step.id)).toStrictEqual(['premium', 'profile', 'summary']);
  });

  it('should title the profile step for a restore differently than for a create', () => {
    expect(get(createSteps('create').current)?.title).toBe('create_account.steps.profile.title');
    expect(get(createSteps('restore', 2).current)?.title).toBe('create_account.steps.profile.restore_title');
  });

  describe('the side panel', () => {
    it('should explain profiles while the path is being chosen', () => {
      expect(get(createSteps().context).title).toBe('create_account.context.entry.title');
    });

    it('should warn about the original password on the restore profile step', () => {
      expect(get(createSteps('restore', 2).context).title).toBe('create_account.context.profile_restore.title');
    });

    it('should explain the password on the create profile step', () => {
      expect(get(createSteps('create', 1).context).title).toBe('create_account.context.profile.title');
    });

    it('should link to the premium account where the keys are found', () => {
      const { context } = createSteps('restore', 1);

      expect(get(context).title).toBe('create_account.context.premium.title');
      expect(get(context).link?.text).toBe('create_account.context.premium.link');
    });

    /** Premium sync carries the profile only, so the summary points at moving the rest by hand. */
    it('should link the restore summary to moving the global database', () => {
      const { context } = createSteps('restore', 3);

      expect(get(context).title).toBe('create_account.context.summary.title');
      expect(get(context).link?.url).toContain('#manually-move-global-database');
    });

    it('should cover the preferences step', () => {
      expect(get(createSteps('create', 2).context).title).toBe('create_account.context.preferences.title');
    });
  });
});

describe('stepPosition', () => {
  it('should give a step its 1-based place within its path', () => {
    expect(stepPosition('restore', 'premium')).toBe(1);
    expect(stepPosition('restore', 'profile')).toBe(2);
    expect(stepPosition('create', 'preferences')).toBe(2);
  });

  it('should have no place for a step the path does not have', () => {
    expect(stepPosition('restore', 'preferences')).toBeUndefined();
    expect(stepPosition('create', 'summary')).toBeUndefined();
  });
});
