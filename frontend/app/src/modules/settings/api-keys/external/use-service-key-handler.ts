import type { Ref } from 'vue';
import type ServiceKey from '@/modules/settings/api-keys/ServiceKey.vue';

interface UseServiceKeyHandlerReturn<T extends InstanceType<typeof ServiceKey>> {
  serviceKeyRef: Ref<T | undefined>;
  saveHandler: () => void;
}

export function useServiceKeyHandler<T extends InstanceType<typeof ServiceKey>>(): UseServiceKeyHandlerReturn<T> {
  const serviceKeyRef = ref<T | undefined>();

  const saveHandler = (): void => {
    const serviceKey = get(serviceKeyRef);
    if (serviceKey) {
      serviceKey.saveHandler();
    }
  };

  return {
    saveHandler,
    // eslint-disable-next-line @rotki/composable-return-readonly -- template ref must be writable
    serviceKeyRef,
  };
}
