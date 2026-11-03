import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useBankAccountLabel } from '@/modules/banks/use-bank-account-label';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

describe('useBankAccountLabel', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  it('should print an account named by its IBAN once, in groups of four', () => {
    const { accountLabel } = useBankAccountLabel();

    expect(accountLabel({ iban: 'DE02120300000000202051', name: 'DE02120300000000202051' })).toEqual({ title: 'DE02 1203 0000 0000 2020 51' });
  });

  it('should put the IBAN under an account with a name of its own', () => {
    const { accountLabel } = useBankAccountLabel();

    expect(accountLabel({ iban: 'de86 6019 9565 1153 4199 37', name: 'Main' })).toEqual({ subtitle: 'DE86 6019 9565 1153 4199 37', title: 'Main' });
  });

  it('should show an account without an IBAN by its name alone', () => {
    const { accountLabel } = useBankAccountLabel();

    expect(accountLabel({ iban: null, name: '202051' })).toEqual({ title: '202051' });
  });

  it('should hide the IBAN and the account number in privacy mode, keeping the country and the shape', () => {
    useSettingsRepo().updateFrontend({ scrambleData: true, scrambleMultiplier: 1.02 });
    const { accountLabel } = useBankAccountLabel();

    const named = accountLabel({ iban: 'DE02120300000000202051', name: 'DE02120300000000202051' });
    expect(named.title).not.toBe('DE02 1203 0000 0000 2020 51');
    expect(named.title).toMatch(/^DE[\dA-Z]{2}( [\dA-Z]{4}){4} [\dA-Z]{2}$/);

    const number = accountLabel({ iban: null, name: '202051' }).title;
    expect(number).not.toBe('202051');
    expect(number).toMatch(/^\d{6}$/);
  });
});
