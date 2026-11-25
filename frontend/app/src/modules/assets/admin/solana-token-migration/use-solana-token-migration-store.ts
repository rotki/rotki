import { get, set } from '@vueuse/shared';
import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useSolanaTokenMigrationStore = defineStore('assets/solana-token-migration', () => {
  const identifiers = ref<string[]>([]);

  const setIdentifiers = (newIdentifiers: string[]): void => {
    set(identifiers, newIdentifiers);
  };

  const clearIdentifiers = (): void => {
    set(identifiers, []);
  };

  const removeIdentifier = (identifier: string): void => {
    const currentIdentifiers = get(identifiers);
    const updatedIdentifiers = currentIdentifiers.filter(id => id !== identifier);
    set(identifiers, updatedIdentifiers);
  };

  return {
    clearIdentifiers,
    identifiers,
    removeIdentifier,
    setIdentifiers,
  };
});
