import type { CreateAccountMode } from '@/modules/auth/create-account/types';
import { describe, expect, it } from 'vitest';
import { type Ref, ref } from 'vue';
import { useCreateAccountWizard } from '@/modules/auth/create-account/use-create-account-wizard';

interface Harness {
  mode: Ref<CreateAccountMode | undefined>;
  step: Ref<number>;
  wizard: ReturnType<typeof useCreateAccountWizard>;
}

function createWizard(step = 1, mode?: CreateAccountMode): Harness {
  const stepRef = ref<number>(step);
  const modeRef = ref<CreateAccountMode | undefined>(mode);
  return { mode: modeRef, step: stepRef, wizard: useCreateAccountWizard(stepRef, modeRef) };
}

describe('useCreateAccountWizard', () => {
  describe('moving between the steps', () => {
    it('should advance to the next step', () => {
      const { step, wizard } = createWizard(2);

      wizard.nextStep();

      expect(get(step)).toBe(3);
    });

    it('should return to the previous step', () => {
      const { step, wizard } = createWizard(3);

      wizard.prevStep();

      expect(get(step)).toBe(2);
    });

    it('should forget the mode when the first step is reached again', () => {
      const { mode, wizard } = createWizard(2, 'restore');

      wizard.prevStep();

      expect(get(mode)).toBeUndefined();
    });

    it('should keep the mode while the first step is not reached', () => {
      const { mode, wizard } = createWizard(3, 'restore');

      wizard.prevStep();

      expect(get(mode)).toBe('restore');
    });

    /**
     * The mode is being chosen again, so the answers the previous choice seeded go with it:
     * a create started from a discarded restore must not carry its database sync.
     */
    it('should drop the premium answers when the first step is reached again', () => {
      const { wizard } = createWizard(1);
      wizard.selectMode('restore');

      wizard.prevStep();

      expect(get(wizard.modelPremiumEnabled)).toBe(false);
      expect(get(wizard.modelPremiumSetupForm)).toEqual({ apiKey: '', apiSecret: '', syncDatabase: false });
    });

    it('should keep the premium answers when an intermediate step is reached', () => {
      const { wizard } = createWizard(2);
      wizard.selectMode('restore');
      set(wizard.modelPremiumSetupForm, { apiKey: 'key', apiSecret: 'secret', syncDatabase: true });

      wizard.prevStep();

      expect(get(wizard.modelPremiumEnabled)).toBe(true);
      expect(get(wizard.modelPremiumSetupForm).apiKey).toBe('key');
    });
  });

  describe('choosing the mode', () => {
    it('should record the mode and move on', () => {
      const { mode, step, wizard } = createWizard(1);

      wizard.selectMode('create');

      expect(get(mode)).toBe('create');
      expect(get(step)).toBe(2);
    });

    it('should leave the premium answers alone when creating', () => {
      const { wizard } = createWizard(1);

      wizard.selectMode('create');

      expect(get(wizard.modelPremiumEnabled)).toBe(false);
      expect(get(wizard.modelPremiumSetupForm).syncDatabase).toBe(false);
    });

    /** Restoring an account means restoring it from the premium sync, so both are answered here. */
    it('should turn on premium and the database sync when restoring', () => {
      const { wizard } = createWizard(1);

      wizard.selectMode('restore');

      expect(get(wizard.modelPremiumEnabled)).toBe(true);
      expect(get(wizard.modelPremiumSetupForm).syncDatabase).toBe(true);
    });

    it('should keep credentials already typed when restoring', () => {
      const { wizard } = createWizard(1);
      set(wizard.modelPremiumSetupForm, { apiKey: 'key', apiSecret: 'secret', syncDatabase: false });

      wizard.selectMode('restore');

      expect(get(wizard.modelPremiumSetupForm)).toEqual({ apiKey: 'key', apiSecret: 'secret', syncDatabase: true });
    });
  });

  describe('isRestoreMode', () => {
    it('should follow the mode', () => {
      const { mode, wizard } = createWizard(1);

      expect(get(wizard.isRestoreMode)).toBe(false);

      set(mode, 'restore');

      expect(get(wizard.isRestoreMode)).toBe(true);
    });

    it('should not treat creating as restoring', () => {
      const { wizard } = createWizard(1, 'create');

      expect(get(wizard.isRestoreMode)).toBe(false);
    });
  });

  describe('buildPayload', () => {
    it('should carry the credentials and the analytics answer', () => {
      const { wizard } = createWizard(4);
      set(wizard.modelCredentialsForm, { password: 'pass', username: 'user' });
      set(wizard.modelSubmitUsageAnalytics, false);

      expect(wizard.buildPayload()).toEqual({
        credentials: { password: 'pass', username: 'user' },
        initialSettings: { submitUsageAnalytics: false },
      });
    });

    it('should omit the premium setup when premium was not asked for', () => {
      const { wizard } = createWizard(4);
      set(wizard.modelPremiumSetupForm, { apiKey: 'key', apiSecret: 'secret', syncDatabase: true });

      expect(wizard.buildPayload().premiumSetup).toBeUndefined();
    });

    it('should send the premium setup when premium was asked for', () => {
      const { wizard } = createWizard(4);
      set(wizard.modelPremiumEnabled, true);
      set(wizard.modelPremiumSetupForm, { apiKey: 'key', apiSecret: 'secret', syncDatabase: true });

      expect(wizard.buildPayload().premiumSetup).toEqual({
        apiKey: 'key',
        apiSecret: 'secret',
        syncDatabase: true,
      });
    });

    it('should submit usage analytics unless the user opts out', () => {
      const { wizard } = createWizard(4);

      expect(wizard.buildPayload().initialSettings.submitUsageAnalytics).toBe(true);
    });
  });
});
