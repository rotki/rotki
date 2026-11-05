import type { BankConnection, BankManifest } from '@/modules/banks/types';
import { toSentenceCase } from '@rotki/common';

export const useBankConnectionsStore = defineStore('banks/connections', () => {
  const manifests = ref<BankManifest[]>([]);
  const connections = ref<BankConnection[]>([]);
  /** Why the supported banks could not be loaded, until a later load succeeds. */
  const manifestsError = shallowRef<unknown>();
  /** Why the connections could not be loaded, until a later load succeeds. */
  const connectionsError = shallowRef<unknown>();

  /** A bank can be added once rotki knows at least one bank it supports. */
  const canAddBank = computed<boolean>(() => get(manifests).length > 0);

  const manifestFor = (connector: string): BankManifest | undefined =>
    get(manifests).find(manifest => manifest.connector === connector);

  /** The manifest display name, or the connector in sentence case before manifests load. */
  const bankNameFor = (connector: string): string =>
    manifestFor(connector)?.displayName ?? toSentenceCase(connector);

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

  return {
    bankNameFor,
    canAddBank,
    connectionName,
    connections,
    connectionsError,
    manifestFor,
    manifests,
    manifestsError,
    setConnections,
    setConnectionsError,
    setManifests,
    setManifestsError,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBankConnectionsStore, import.meta.hot));
