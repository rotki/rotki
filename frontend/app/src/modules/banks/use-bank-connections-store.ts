import type { BankConnection, BankManifest } from '@/modules/banks/types';
import { toSentenceCase } from '@rotki/common';

export const useBankConnectionsStore = defineStore('banks/connections', () => {
  const manifests = ref<BankManifest[]>([]);
  const connections = ref<BankConnection[]>([]);

  const manifestFor = (location: string): BankManifest | undefined =>
    get(manifests).find(manifest => manifest.location === location);

  /** The bank's manifest display name, or its location in sentence case while the manifests have not loaded. */
  const bankNameFor = (location: string): string =>
    manifestFor(location)?.displayName ?? toSentenceCase(location);

  const setManifests = (value: BankManifest[]): void => {
    set(manifests, value);
  };

  const setConnections = (value: BankConnection[]): void => {
    set(connections, value);
  };

  return {
    bankNameFor,
    connections,
    manifestFor,
    manifests,
    setConnections,
    setManifests,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBankConnectionsStore, import.meta.hot));
