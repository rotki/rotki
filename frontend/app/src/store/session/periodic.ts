export const usePeriodicStore = defineStore('session/periodic', () => {
  const lastBalanceSave = ref<number>(0);
  const lastDataUpload = ref<number>(0);
  const connectedNodes = shallowRef<Record<string, string[]>>({});
  const failedToConnect = shallowRef<Record<string, string[]>>({});

  return {
    connectedNodes,
    failedToConnect,
    lastBalanceSave,
    lastDataUpload,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(usePeriodicStore, import.meta.hot));
