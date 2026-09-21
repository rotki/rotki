import type { BankConnection, BankManifest } from '@/modules/banks/types';
import { toSentenceCase } from '@rotki/common';

export const useBankConnectionsStore = defineStore('banks/connections', () => {
  const manifests = ref<BankManifest[]>([]);
  const connections = ref<BankConnection[]>([]);
  /** The locations the last bank balance query filled, which a later one replaces. */
  const balanceLocations = ref<string[]>([]);

  /** The locations the connected banks put their balances and history in. */
  const bankLocations = computed<string[]>(() => [...new Set(get(connections).map(connection => connection.location))]);

  const manifestFor = (connector: string): BankManifest | undefined =>
    get(manifests).find(manifest => manifest.connectorIdentifier === connector);

  /** The connector's display name, or its identifier in sentence case while the manifests have not loaded. */
  const bankNameFor = (connector: string): string =>
    manifestFor(connector)?.displayName ?? toSentenceCase(connector);

  /** The connector of a connection, or an empty string if it is not loaded. */
  const connectorOf = (identifier: string): string =>
    get(connections).find(connection => connection.identifier === identifier)?.connector ?? '';

  /** The user given name of a connection, or its identifier if it is not loaded. */
  const connectionName = (identifier: string): string =>
    get(connections).find(connection => connection.identifier === identifier)?.name ?? identifier;

  const setManifests = (value: BankManifest[]): void => {
    set(manifests, value);
  };

  const setConnections = (value: BankConnection[]): void => {
    set(connections, value);
  };

  const setBalanceLocations = (value: string[]): void => {
    set(balanceLocations, value);
  };

  return {
    balanceLocations,
    bankLocations,
    bankNameFor,
    connectionName,
    connections,
    connectorOf,
    manifestFor,
    manifests,
    setBalanceLocations,
    setConnections,
    setManifests,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBankConnectionsStore, import.meta.hot));
