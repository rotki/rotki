import type { BankManifest } from '@/modules/banks/types';
import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';

describe('useBankConnectionsStore', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  it('should name a bank by its manifest display name', () => {
    const store = useBankConnectionsStore();
    store.setManifests([createMock<BankManifest>({ displayName: 'Qonto Business', location: 'qonto' })]);
    expect(store.bankNameFor('qonto')).toBe('Qonto Business');
  });

  it('should fall back to the location in sentence case for a bank without a loaded manifest', () => {
    const store = useBankConnectionsStore();
    store.setManifests([createMock<BankManifest>({ displayName: 'Qonto Business', location: 'qonto' })]);
    expect(store.bankNameFor('revolut')).toBe('Revolut');
  });
});
