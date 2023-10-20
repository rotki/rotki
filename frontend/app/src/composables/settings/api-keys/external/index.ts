import { type MaybeRef } from '@vueuse/core';
import {
  type ExternalServiceKeys,
  type ExternalServiceName
} from '@/types/user';

const getName = (name: ExternalServiceName, chain?: string) => {
  if (name === 'etherscan') {
    assert(chain, 'chain is missing for etherscan');
    if (chain === 'ethereum') {
      return name;
    }
    return `${chain}_${name}`;
  }
  return name;
};

type Status = { message: string; success?: boolean };

export const useExternalApiKeys = createSharedComposable(
  (t: ReturnType<typeof useI18n>['t']) => {
    const loading = ref(false);
    const keys = ref<ExternalServiceKeys>();
    const status = ref<Record<string, Status>>({});

    const { show } = useConfirmStore();
    const {
      setExternalServices,
      deleteExternalServices,
      queryExternalServices
    } = useExternalServicesApi();

    const apiKey = (
      name: MaybeRef<ExternalServiceName>,
      chain?: MaybeRef<string>
    ): ComputedRef<string> =>
      computed(() => {
        const items = get(keys);
        const service = get(name);
        if (!items) {
          return '';
        } else if (service === 'etherscan') {
          const chainId = get(chain);
          assert(chainId, 'missing chain for etherscan');
          return items[service]?.[transformCase(chainId, true)]?.apiKey || '';
        }
        return items[service]?.apiKey || '';
      });

    const actionStatus = (
      name: MaybeRef<ExternalServiceName>,
      chain?: MaybeRef<string>
    ): ComputedRef<Status | undefined> =>
      computed(() => {
        const key = getName(get(name), get(chain));
        return get(status)[key];
      });

    const load = async () => {
      set(loading, true);
      try {
        set(keys, await queryExternalServices());
      } catch (e) {
        logger.error(e);
      } finally {
        set(loading, false);
      }
    };

    const resetStatus = (key: string) => {
      const { [key]: service, ...newStatus } = get(status);
      set(status, newStatus);
    };

    const setStatus = (key: string, message: Status) => {
      setTimeout(() => resetStatus(key), 4500);

      set(status, {
        ...get(status),
        [key]: message
      });
    };
    const save = async ({ name, apiKey }: { name: string; apiKey: string }) => {
      resetStatus(name);
      try {
        set(loading, true);
        set(keys, await setExternalServices([{ name, apiKey: apiKey.trim() }]));
        setStatus(name, {
          success: true,
          message: t('external_services.set.success.message', {
            serviceName: toCapitalCase(name.split('_').join(' '))
          })
        });
      } catch (e: any) {
        setStatus(name, {
          message: t('external_services.set.error.message', {
            error: e.message
          })
        });
      } finally {
        set(loading, false);
      }
    };

    const confirmDelete = (
      name: string,
      postConfirmAction?: () => Promise<void> | void
    ) => {
      resetStatus(name);
      show(
        {
          title: t('external_services.confirmation.title'),
          message: t('external_services.confirmation.message'),
          type: 'info'
        },
        async () => {
          await deleteService(name);
          await postConfirmAction?.();
        }
      );
    };

    const deleteService = async (name: string) => {
      set(loading, true);
      try {
        set(keys, await deleteExternalServices(name));
      } catch (e: any) {
        setStatus(name, {
          message: t('external_services.delete_error.description', {
            message: e.message
          })
        });
      } finally {
        set(loading, false);
      }
    };

    return {
      loading,
      getName,
      apiKey,
      actionStatus,
      load,
      save,
      confirmDelete
    };
  }
);
