import { get } from '@vueuse/shared';
import { defineStore } from 'pinia';
import { computed, shallowRef } from 'vue';

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
