import type { QueriedAddresses } from '@/modules/session/types';
import type { Tag, Tags } from '@/modules/tags/tags';

export const useSessionMetadataStore = defineStore('session/metadata', () => {
  // Periodic data
  const lastBalanceSave = ref<number>(0);
  const lastDataUpload = ref<number>(0);
  const connectedNodes = shallowRef<Record<string, string[]>>({});
  const coolingDownNodes = shallowRef<Record<string, string[]>>({});
  const failedToConnect = shallowRef<Record<string, string[]>>({});

  // Tags
  const allTags = ref<Tags>({});
  const tags = computed<Tag[]>(() => Object.values(get(allTags)));

  // Queried addresses
  const queriedAddresses = ref<QueriedAddresses>({});

  return {
    allTags,
    connectedNodes,
    coolingDownNodes,
    failedToConnect,
    lastBalanceSave,
    lastDataUpload,
    queriedAddresses,
    tags,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSessionMetadataStore, import.meta.hot));
