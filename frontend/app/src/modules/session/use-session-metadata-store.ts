import type { QueriedAddresses } from '@/modules/session/types';
import type { Tag, Tags } from '@/modules/tags/tags';
import { get } from '@vueuse/shared';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { computed, ref, shallowRef } from 'vue';

export const useSessionMetadataStore = defineStore('session/metadata', () => {
  const lastBalanceSave = ref<number>(0);
  const lastDataUpload = ref<number>(0);
  /** When this session last asked the server for its backup because none was known, in ms. */
  const lastRemoteBackupCheck = ref<number>(0);
  const connectedNodes = shallowRef<Record<string, string[]>>({});
  const coolingDownNodes = shallowRef<Record<string, string[]>>({});
  const failedToConnect = shallowRef<Record<string, string[]>>({});

  const allTags = ref<Tags>({});
  const tags = computed<Tag[]>(() => Object.values(get(allTags)));

  const queriedAddresses = ref<QueriedAddresses>({});

  return {
    allTags,
    connectedNodes,
    coolingDownNodes,
    failedToConnect,
    lastBalanceSave,
    lastDataUpload,
    lastRemoteBackupCheck,
    queriedAddresses,
    tags,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSessionMetadataStore, import.meta.hot));
