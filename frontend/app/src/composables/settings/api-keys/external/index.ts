import type { Auth, ExternalServiceKey, ExternalServiceKeys, ExternalServiceName } from '@/types/user';
import type { MaybeRef } from '@vueuse/core';

function getName(name: ExternalServiceName, chain?: string): string {
  if (name === 'etherscan' || name === 'blockscout') {
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
  credential: (name: MaybeRef<ExternalServiceName>) => ComputedRef<Auth | null>;
  actionStatus: (name: MaybeRef<ExternalServiceName>, chain?: MaybeRef<string>) => ComputedRef<Status | undefined>;
  load: () => Promise<void>;
  save: (payload: ExternalServiceKey, postConfirmAction?: () => Promise<void> | void) => Promise<void>;
  confirmDelete: (name: string, postConfirmAction?: () => Promise<void> | void) => void;
  keys: Ref<ExternalServiceKeys | undefined>;
}

export const useExternalApiKeys = createSharedComposable((t: ReturnType<typeof useI18n>['t']): UseExternalApiKeysReturn => {
  const loading = ref(false);
  const keys = ref<ExternalServiceKeys>();
  const status = ref<Record<string, Status>>({});

  const { show } = useConfirmStore();
  const { setExternalServices, deleteExternalServices, queryExternalServices } = useExternalServicesApi();

  const apiKey = (
    name: MaybeRef<ExternalServiceName>,
    chain?: MaybeRef<string>,
  ): ComputedRef<string> => computed(() => {
    const items = get(keys);
    const service = get(name);

    if (!items)
      return '';

    if (service === 'etherscan' || service === 'blockscout') {
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

  const credential = (name: MaybeRef<ExternalServiceName>): ComputedRef<Auth | null> => computed(() => {
    const items = get(keys);
    const service = get(name);

    if (!items || service === 'etherscan' || service === 'blockscout')
      return null;

    const itemService = items[service];

    if (itemService && 'username' in itemService)
      return itemService;

    return null;
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
    const isPayloadWithCredential = 'username' in payload;
    resetStatus(name);
    try {
      set(loading, true);
      set(keys, await setExternalServices([payload]));

      const serviceName = toCapitalCase(name.split('_').join(' '));

      setStatus(name, {
        success: true,
        message: isPayloadWithCredential
          ? t('external_services.set_credential.success.message', {
            serviceName,
          })
          : t('external_services.set.success.message', {
            serviceName,
          }),
      });
      await postConfirmAction?.();
    }
    catch (error: any) {
      const errorMessage = error.message;
      setStatus(name, {
        message: isPayloadWithCredential
          ? t('external_services.set_credential.error.message', {
            error: errorMessage,
          })
          : t('external_services.set.error.message', {
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

  const confirmDelete = (name: string, postConfirmAction?: () => Promise<void> | void): void => {
    resetStatus(name);
    show(
      {
        title: t('external_services.confirmation.title'),
        message: t('external_services.confirmation.message'),
        type: 'info',
      },
      async () => {
        await deleteService(name);
        await postConfirmAction?.();
      },
    );
  };

  return {
    loading,
    getName,
    apiKey,
    credential,
    actionStatus,
    load,
    save,
    confirmDelete,
    keys,
  };
});
