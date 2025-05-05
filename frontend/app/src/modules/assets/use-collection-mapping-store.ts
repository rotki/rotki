import { defineStore } from 'pinia';

export const useCollectionMappingStore = defineStore('asset/collection-mapping', () => {
  const collectionMainAsset = ref<Record<string, string>>({});
  const assetToCollection = ref<Record<string, string>>({});

  return {
    assetToCollection,
    collectionMainAsset,
  };
});
