import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef, Ref } from 'vue';
import type ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import type { ConfirmationMessage } from '@/modules/history/events/composables/use-deletion-strategies';
import type { ExternalServiceKey, ExternalServiceKeys, ExternalServiceName } from '@/types/user';
import { assert, toCapitalCase, transformCase } from '@rotki/common';
import { useExternalServicesApi } from '@/composables/api/settings/external-services-api';
import { useConfirmStore } from '@/store/confirm';
import { DialogType } from '@/types/dialogs';
import { logger } from '@/utils/logging';

function getName(name: ExternalServiceName, chain?: string): string {
  if (name === 'blockscout') {
    assert(chain, `chain is missing for ${name}`);
    if (chain === 'ethereum')
      return name;
    return `${chain}_${name}`;
  }
  return name;
}

interface Status {
  message: string;
  success?: boolean;
}

interface UseExternalApiKeysReturn {
  loading: Ref<boolean>;
  getName: (name: ExternalServiceName, chain?: string) => string;
  apiKey: (name: MaybeRef<ExternalServiceName>, chain?: MaybeRef<string>) => ComputedRef<string>;
  actionStatus: (name: MaybeRef<ExternalServiceName>, chain?: MaybeRef<string>) => ComputedRef<Status | undefined>;
  load: () => Promise<void>;
  save: (payload: ExternalServiceKey, postConfirmAction?: () => Promise<void> | void) => Promise<void>;
  confirmDelete: (name: string, postConfirmAction?: () => Promise<void> | void, confirmation?: Partial<ConfirmationMessage>) => void;
  keys: Ref<ExternalServiceKeys | undefined>;
}

export const useExternalApiKeys = createSharedComposable((t: ReturnType<typeof useI18n>['t']): UseExternalApiKeysReturn => {
  const loading = ref(false);
  const keys = ref<ExternalServiceKeys>();
  const status = ref<Record<string, Status>>({});

  const { show } = useConfirmStore();
  const { deleteExternalServices, queryExternalServices, setExternalServices } = useExternalServicesApi();

  const apiKey = (
    name: MaybeRef<ExternalServiceName>,
    chain?: MaybeRef<string>,
  ): ComputedRef<string> => computed(() => {
    const items = get(keys);
    const service = get(name);

    if (!items)
      return '';

    if (service === 'blockscout') {
      const itemService = items[service];
      const chainId = get(chain);
      assert(chainId, `missing chain for ${service}`);

      const transformedChainId = transformCase(chainId, true);

      if (itemService && transformedChainId in itemService) {
        const chainData = itemService[transformedChainId];
        if (chainData && 'apiKey' in chainData)
          return chainData.apiKey || '';
      }
    }
    else {
      const itemService = items[service];

      if (itemService && 'apiKey' in itemService)
        return itemService.apiKey || '';
    }

    return '';
  });

  const actionStatus = (
    name: MaybeRef<ExternalServiceName>,
    chain?: MaybeRef<string>,
  ): ComputedRef<Status | undefined> => computed(() => {
    const key = getName(get(name), get(chain));
    return get(status)[key];
  });

  const load = async (): Promise<void> => {
    set(loading, true);
    try {
      set(keys, await queryExternalServices());
    }
    catch (error) {
      logger.error(error);
    }
    finally {
      set(loading, false);
    }
  };

  const resetStatus = (key: string): void => {
    const { [key]: service, ...newStatus } = get(status);
    set(status, newStatus);
  };

  const setStatus = (key: string, message: Status): void => {
    setTimeout(() => resetStatus(key), 4500);

    set(status, {
      ...get(status),
      [key]: message,
    });
  };

  const save = async (payload: ExternalServiceKey, postConfirmAction?: () => Promise<void> | void): Promise<void> => {
    const { name } = payload;
    resetStatus(name);
    try {
      set(loading, true);
      set(keys, await setExternalServices([payload]));

      const serviceName = toCapitalCase(name.split('_').join(' '));

      setStatus(name, {
        message: t('external_services.set.success.message', {
          serviceName,
        }),
        success: true,
      });
      await postConfirmAction?.();
    }
    catch (error: any) {
      const errorMessage = error.message;
      setStatus(name, {
        message: t('external_services.set.error.message', {
          error: errorMessage,
        }),
      });
    }
    finally {
      set(loading, false);
    }
  };

  const deleteService = async (name: string): Promise<void> => {
    set(loading, true);
    try {
      set(keys, await deleteExternalServices(name));
    }
    catch (error: any) {
      setStatus(name, {
        message: t('external_services.delete_error.description', {
          message: error.message,
        }),
      });
    }
    finally {
      set(loading, false);
    }
  };

  const confirmDelete = (name: string, postConfirmAction?: () => Promise<void> | void, confirmation: Partial<ConfirmationMessage> = {}): void => {
    resetStatus(name);
    show(
      {
        message: t('external_services.confirmation.message'),
        title: t('external_services.confirmation.title'),
        ...confirmation,
        type: DialogType.WARNING,
      },
      async () => {
        await deleteService(name);
        await postConfirmAction?.();
      },
    );
  };

  return {
    actionStatus,
    apiKey,
    confirmDelete,
    getName,
    keys,
    load,
    loading,
    save,
  };
});

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
    serviceKeyRef,
  };
}
