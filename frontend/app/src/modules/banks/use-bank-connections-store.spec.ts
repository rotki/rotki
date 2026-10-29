import type { BankConnection, BankManifest } from '@/modules/banks/types';
import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';

describe('useBankConnectionsStore', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  it('should name a bank connector by its manifest display name', () => {
    const store = useBankConnectionsStore();
    store.setManifests([createMock<BankManifest>({ displayName: 'Qonto Business', connector: 'qonto' })]);
    expect(store.bankNameFor('qonto')).toBe('Qonto Business');
  });

  it('should fall back to the connector in sentence case without a loaded manifest', () => {
    expect(useBankConnectionsStore().bankNameFor('revolut')).toBe('Revolut');
  });

  it('should resolve stable connection identifiers to their connector and name', () => {
    const store = useBankConnectionsStore();
    store.setConnections([
      createMock<BankConnection>({ connector: 'fints', identifier: 'c1', name: 'ING main' }),
      createMock<BankConnection>({ connector: 'fints', identifier: 'c2', name: 'ING savings' }),
    ]);
    expect(store.connectorOf('c1')).toBe('fints');
    expect(store.connectionName('c2')).toBe('ING savings');
    expect(store.connectorOf('missing')).toBe('');
    expect(store.connectionName('missing')).toBe('missing');
  });
});
