import type { CreateAccountMode } from '@/modules/auth/create-account/types';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import { useCreateAccountWizard } from '@/modules/auth/create-account/use-create-account-wizard';

interface Harness {
  mode: Ref<CreateAccountMode | undefined>;
  step: Ref<number>;
  wizard: ReturnType<typeof useCreateAccountWizard>;
}

function createWizard(step: number = 1, mode?: CreateAccountMode): Harness {
  const stepRef = ref<number>(step);
  const modeRef = ref<CreateAccountMode | undefined>(mode);
  return { mode: modeRef, step: stepRef, wizard: useCreateAccountWizard(stepRef, modeRef) };
}

function fillPremium(wizard: Harness['wizard']): void {
  set(wizard.modelPremiumEnabled, true);
  set(wizard.modelPremiumSetupForm, { ...get(wizard.modelPremiumSetupForm), apiKey: 'key', apiSecret: 'secret' });
}

describe('useCreateAccountWizard', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('choosing a path', () => {
    it('should start the chosen path on its first step', () => {
      const { mode, step, wizard } = createWizard(3);

      wizard.selectMode('create');

      expect(get(mode)).toBe('create');
      expect(get(step)).toBe(1);
    });

    it('should turn on premium and the database download for a restore', () => {
      const { wizard } = createWizard();

      wizard.selectMode('restore');

      expect(get(wizard.modelPremiumEnabled)).toBe(true);
      expect(get(wizard.modelPremiumSetupForm).syncDatabase).toBe(true);
    });
  });

  describe('moving between the steps', () => {
    it('should advance to the next step', () => {
      const { step, wizard } = createWizard(1, 'restore');

      wizard.nextStep();

      expect(get(step)).toBe(2);
    });

    it('should return to the previous step', () => {
      const { mode, step, wizard } = createWizard(2, 'restore');

      wizard.prevStep();

      expect(get(step)).toBe(1);
      expect(get(mode)).toBe('restore');
    });

    it('should return to the path choice from the first step', () => {
      const { mode, step, wizard } = createWizard(1, 'create');

      wizard.prevStep();

      expect(get(mode)).toBeUndefined();
      expect(get(step)).toBe(1);
    });

    /** A restore seeds a database download, which must not reach a create chosen afterwards. */
    it('should drop the premium answers a restore seeded once the path is chosen again', () => {
      const { wizard } = createWizard();
      wizard.selectMode('restore');

      wizard.prevStep();
      wizard.selectMode('create');

      expect(get(wizard.modelPremiumEnabled)).toBe(false);
      expect(get(wizard.modelPremiumSetupForm).syncDatabase).toBe(false);
    });

    it('should jump back to a named step of the chosen path', () => {
      const { step, wizard } = createWizard(3, 'restore');

      wizard.goToStep('premium');

      expect(get(step)).toBe(1);
    });

    /** A new profile picks its own password; a restore needs the synced profile's. */
    it('should forget the password, but not the name, once the path is chosen again', () => {
      const { wizard } = createWizard(1, 'create');
      set(wizard.modelCredentialsForm, { password: 'secret', username: 'user' });
      set(wizard.modelPasswordConfirm, 'secret');
      set(wizard.modelUserPrompted, true);

      wizard.prevStep();
      wizard.selectMode('restore');

      expect(get(wizard.modelCredentialsForm)).toStrictEqual({ password: '', username: 'user' });
      expect(get(wizard.modelPasswordConfirm)).toBe('');
      expect(get(wizard.modelUserPrompted)).toBe(false);
    });

    it('should keep the password while moving within a path', () => {
      const { wizard } = createWizard(2, 'restore');
      set(wizard.modelCredentialsForm, { password: 'secret', username: 'user' });

      wizard.prevStep();

      expect(get(wizard.modelCredentialsForm).password).toBe('secret');
    });

    it('should ignore a jump to a step the chosen path does not have', () => {
      const { mode, step, wizard } = createWizard(3, 'restore');

      wizard.goToStep('preferences');

      expect(get(step)).toBe(3);
      expect(get(mode)).toBe('restore');
    });

    it('should ignore a jump while no path is chosen', () => {
      const { step, wizard } = createWizard(1);

      wizard.goToStep('summary');

      expect(get(step)).toBe(1);
    });
  });

  describe('the payload of a create', () => {
    it('should carry the credentials, the currency and the analytics choice', () => {
      const { wizard } = createWizard(2, 'create');
      set(wizard.modelCredentialsForm, { password: 'pass', username: 'user' });
      set(wizard.modelMainCurrency, 'EUR');
      set(wizard.modelSubmitUsageAnalytics, false);

      expect(wizard.buildPayload()).toStrictEqual({
        credentials: { password: 'pass', username: 'user' },
        initialSettings: { mainCurrency: 'EUR', submitUsageAnalytics: false },
      });
    });

    it('should start in the currency the system locale suggests, with analytics on', () => {
      vi.spyOn(navigator, 'language', 'get').mockReturnValue('de-DE');
      const { wizard } = createWizard(2, 'create');

      expect(wizard.buildPayload().initialSettings).toStrictEqual({ mainCurrency: 'EUR', submitUsageAnalytics: true });
    });

    it('should send premium credentials without downloading a database', () => {
      const { wizard } = createWizard(2, 'create');
      fillPremium(wizard);

      expect(wizard.buildPayload().premiumSetup).toStrictEqual({ apiKey: 'key', apiSecret: 'secret', syncDatabase: false });
    });

    it('should treat an opened premium section left empty as no premium', () => {
      const { wizard } = createWizard(2, 'create');
      set(wizard.modelPremiumEnabled, true);
      set(wizard.modelPremiumShouldSync, true);

      const payload = wizard.buildPayload();

      expect(payload.premiumSetup).toBeUndefined();
      expect(payload.initialSettings).not.toHaveProperty('premiumShouldSync');
    });

    it('should leave out credentials typed into a section that was closed again', () => {
      const { wizard } = createWizard(2, 'create');
      fillPremium(wizard);
      set(wizard.modelPremiumEnabled, false);

      expect(wizard.buildPayload().premiumSetup).toBeUndefined();
    });

    it('should turn on automatic backups only when premium is given and backups are asked for', () => {
      const { wizard } = createWizard(2, 'create');
      fillPremium(wizard);
      set(wizard.modelPremiumShouldSync, true);

      expect(wizard.buildPayload().initialSettings).toHaveProperty('premiumShouldSync', true);
    });

    /** Sending false would switch backups off; leaving the key out keeps the backend default. */
    it('should never send automatic backups as off', () => {
      const { wizard } = createWizard(2, 'create');
      fillPremium(wizard);

      expect(wizard.buildPayload().initialSettings).not.toHaveProperty('premiumShouldSync');
    });
  });

  describe('the payload of a restore', () => {
    it('should always carry the premium setup with the database download', () => {
      const { wizard } = createWizard();
      wizard.selectMode('restore');
      set(wizard.modelPremiumSetupForm, { ...get(wizard.modelPremiumSetupForm), apiKey: 'key', apiSecret: 'secret' });

      expect(wizard.buildPayload().premiumSetup).toStrictEqual({ apiKey: 'key', apiSecret: 'secret', syncDatabase: true });
    });

    /** The downloaded database replaces the one these would be written to, so the backup's own apply. */
    it('should send no settings at all', () => {
      const { wizard } = createWizard();
      wizard.selectMode('restore');
      set(wizard.modelMainCurrency, 'EUR');
      set(wizard.modelPremiumShouldSync, true);

      expect(wizard.buildPayload().initialSettings).toStrictEqual({});
    });
  });
});
