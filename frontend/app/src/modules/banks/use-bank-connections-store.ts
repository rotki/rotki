import type { BankConnection, BankConnectionBalances, BankManifest } from '@/modules/banks/types';
import { toSentenceCase } from '@rotki/common';

export const useBankConnectionsStore = defineStore('banks/connections', () => {
  const manifests = ref<BankManifest[]>([]);
  const connections = ref<BankConnection[]>([]);
  const connectionBalances = ref<BankConnectionBalances[]>([]);
  /** Why the supported banks could not be loaded, until a later load succeeds. */
  const manifestsError = shallowRef<unknown>();
  /** Why the connections could not be loaded, until a later load succeeds. */
  const connectionsError = shallowRef<unknown>();

  const manifestFor = (connector: string): BankManifest | undefined =>
    get(manifests).find(manifest => manifest.connector === connector);

  /** The manifest display name, or the connector in sentence case before manifests load. */
  const bankNameFor = (connector: string): string =>
    manifestFor(connector)?.displayName ?? toSentenceCase(connector);

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

  const setConnectionBalances = (value: BankConnectionBalances[]): void => {
    set(connectionBalances, value);
  };

  return {
    bankNameFor,
    connectionBalances,
    connections,
    connectionsError,
    manifestFor,
    manifests,
    manifestsError,
    setConnections,
    setConnectionBalances,
    setConnectionsError,
    setManifests,
    setManifestsError,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBankConnectionsStore, import.meta.hot));
