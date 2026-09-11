import type { BankConnection, BankManifest } from '@/modules/banks/types';

export const useBankConnectionsStore = defineStore('banks/connections', () => {
  const manifests = ref<BankManifest[]>([]);
  const connections = ref<BankConnection[]>([]);

  const manifestFor = (location: string): BankManifest | undefined =>
    get(manifests).find(manifest => manifest.location === location);

  const setManifests = (value: BankManifest[]): void => {
    set(manifests, value);
  };

  const setConnections = (value: BankConnection[]): void => {
    set(connections, value);
  };

  return {
    connections,
    manifestFor,
    manifests,
    setConnections,
    setManifests,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBankConnectionsStore, import.meta.hot));
