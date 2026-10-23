import type { BankConnection, BankManifest } from '@/modules/banks/types';
import { toSentenceCase } from '@rotki/common';

export const useBankConnectionsStore = defineStore('banks/connections', () => {
  const manifests = ref<BankManifest[]>([]);
  const connections = ref<BankConnection[]>([]);
  /** Why the supported banks could not be loaded, until a later load succeeds. */
  const manifestsError = shallowRef<unknown>();
  /** Why the connections could not be loaded, until a later load succeeds. */
  const connectionsError = shallowRef<unknown>();

  const manifestFor = (location: string): BankManifest | undefined =>
    get(manifests).find(manifest => manifest.location === location);

  /** The bank's manifest display name, or its location in sentence case while the manifests have not loaded. */
  const bankNameFor = (location: string): string =>
    manifestFor(location)?.displayName ?? toSentenceCase(location);

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
