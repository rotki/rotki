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
    store.setManifests([createMock<BankManifest>({ displayName: 'Qonto Business', connectorIdentifier: 'qonto' })]);
    expect(store.bankNameFor('qonto')).toBe('Qonto Business');
  });

  it('should fall back to the connector in sentence case for a connector without a loaded manifest', () => {
    const store = useBankConnectionsStore();
    store.setManifests([createMock<BankManifest>({ displayName: 'Qonto Business', connectorIdentifier: 'qonto' })]);
    expect(store.bankNameFor('revolut')).toBe('Revolut');
  });

  it('should resolve a connection identifier to its connector and name, and list the locations of the connections once', () => {
    const store = useBankConnectionsStore();
    store.setConnections([
      createMock<BankConnection>({ connector: 'fints', identifier: 'c1', location: 'custom:ing', name: 'ING main' }),
      createMock<BankConnection>({ connector: 'fints', identifier: 'c2', location: 'custom:ing', name: 'ING savings' }),
      createMock<BankConnection>({ connector: 'qonto', identifier: 'c3', location: 'qonto', name: 'Qonto' }),
    ]);
    expect(store.connectorOf('c1')).toBe('fints');
    expect(store.connectionName('c2')).toBe('ING savings');
    expect(store.connectorOf('missing')).toBe('');
    expect(store.connectionName('missing')).toBe('missing');
    expect(store.bankLocations).toEqual(['custom:ing', 'qonto']);
  });
});
