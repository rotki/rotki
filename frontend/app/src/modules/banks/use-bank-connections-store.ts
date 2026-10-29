import type { BankConnection, BankManifest } from '@/modules/banks/types';
import { toSentenceCase } from '@rotki/common';

export const useBankConnectionsStore = defineStore('banks/connections', () => {
  const manifests = ref<BankManifest[]>([]);
  const connections = ref<BankConnection[]>([]);
  /** Why the supported banks could not be loaded, until a later load succeeds. */
  const manifestsError = shallowRef<unknown>();
  /** Why the connections could not be loaded, until a later load succeeds. */
  const connectionsError = shallowRef<unknown>();
  /** The locations the last bank balance query filled, which a later one replaces. */
  const balanceLocations = ref<string[]>([]);

  /** The locations the connected banks put their balances and history in. */
  const bankLocations = computed<string[]>(() => [...new Set(get(connections).map(connection => connection.location))]);

  /** The locations bank balances come from: those of the connections, and every fixed connector location. */
  const bankBalanceLocations = computed<string[]>(() => [...new Set([
    ...get(bankLocations),
    ...get(manifests).flatMap(({ fixedLocation }) => (fixedLocation ? [fixedLocation] : [])),
  ])]);

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
    set(manifestsError, undefined);
  };

  const setManifestsError = (error: unknown): void => {
    set(manifestsError, error);
  };

  const setConnections = (value: BankConnection[]): void => {
    set(connections, value);
    set(connectionsError, undefined);
  };

  const setConnectionsError = (error: unknown): void => {
    set(connectionsError, error);
  };

  const setBalanceLocations = (value: string[]): void => {
    set(balanceLocations, value);
  };

  return {
    balanceLocations,
    bankBalanceLocations,
    bankLocations,
    bankNameFor,
    connectionName,
    connections,
    connectionsError,
    connectorOf,
    manifestFor,
    manifests,
    manifestsError,
    setBalanceLocations,
    setConnections,
    setConnectionsError,
    setManifests,
    setManifestsError,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBankConnectionsStore, import.meta.hot));
