import { defineStore } from 'pinia';

export const useCollectionMappingStore = defineStore('asset/collection-mapping', () => {
  const collectionMainAsset = shallowRef<Record<string, string>>({});
  const assetToCollection = shallowRef<Record<string, string>>({});

  const collectionMainAssets = computed<string[]>(() => Object.values(get(collectionMainAsset)));

  return {
    assetToCollection,
    collectionMainAsset,
    collectionMainAssets,
  };
});
