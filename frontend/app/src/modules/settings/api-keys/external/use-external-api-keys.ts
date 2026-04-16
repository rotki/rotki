import type { ComputedRef, DeepReadonly, MaybeRefOrGetter, Ref } from 'vue';
import type { ConfirmationMessage } from '@/modules/history/events/use-deletion-strategies';
import type { ExternalServiceKey, ExternalServiceKeys, ExternalServiceName } from '@/modules/integrations/types';
import { toCapitalCase } from '@rotki/common';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { DialogType } from '@/modules/core/common/dialogs';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useExternalServicesApi } from '@/modules/settings/api/use-external-services-api';

function getName(name: ExternalServiceName, _chain?: string): string {
  return name;
}

interface Status {
  message: string;
  success?: boolean;
}

interface UseExternalApiKeysReturn {
  readonly loading: DeepReadonly<Ref<boolean>>;
  getName: (name: ExternalServiceName, chain?: string) => string;
  getApiKey: (name: ExternalServiceName, chain?: string) => string;
  useApiKey: (name: MaybeRefOrGetter<ExternalServiceName>, chain?: MaybeRefOrGetter<string>) => ComputedRef<string>;
  actionStatus: (name: MaybeRefOrGetter<ExternalServiceName>, chain?: MaybeRefOrGetter<string>) => ComputedRef<Status | undefined>;
  load: () => Promise<void>;
  save: (payload: ExternalServiceKey, postConfirmAction?: () => Promise<void> | void) => Promise<void>;
  confirmDelete: (name: string, postConfirmAction?: () => Promise<void> | void, confirmation?: Partial<ConfirmationMessage>) => void;
  readonly keys: DeepReadonly<Ref<ExternalServiceKeys | undefined>>;
}

export const useExternalApiKeys = createSharedComposable((): UseExternalApiKeysReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const loading = ref<boolean>(false);
  const status = ref<Record<string, Status>>({});
  const keys = ref<ExternalServiceKeys>();

  const { show } = useConfirmStore();
  const { deleteExternalServices, queryExternalServices, setExternalServices } = useExternalServicesApi();

  const { logged } = storeToRefs(useSessionAuthStore());

  function getApiKey(name: ExternalServiceName, _chain?: string): string {
    const items = get(keys);
    if (!items)
      return '';

    const itemService = items[name];
    if (itemService && 'apiKey' in itemService)
      return itemService.apiKey || '';

    return '';
  }

  function useApiKey(
    name: MaybeRefOrGetter<ExternalServiceName>,
    chain?: MaybeRefOrGetter<string>,
  ): ComputedRef<string> {
    return computed<string>(() => getApiKey(toValue(name), toValue(chain)));
  }

  function actionStatus(
    name: MaybeRefOrGetter<ExternalServiceName>,
    chain?: MaybeRefOrGetter<string>,
  ): ComputedRef<Status | undefined> {
    return computed<Status | undefined>(() => {
      const key = getName(toValue(name), toValue(chain));
      return get(status)[key];
    });
  }

  async function load(): Promise<void> {
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
  }

  function resetStatus(key: string): void {
    const { [key]: removed, ...newStatus } = get(status);
    set(status, newStatus);
  }

  function setStatus(key: string, message: Status): void {
    setTimeout(() => resetStatus(key), 4500);

    set(status, {
      ...get(status),
      [key]: message,
    });
  }

  async function save(payload: ExternalServiceKey, postConfirmAction?: () => Promise<void> | void): Promise<void> {
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
    catch (error: unknown) {
      const errorMessage = getErrorMessage(error);
      setStatus(name, {
        message: t('external_services.set.error.message', {
          error: errorMessage,
        }),
      });
    }
    finally {
      set(loading, false);
    }
  }

  async function deleteService(name: string): Promise<void> {
    set(loading, true);
    try {
      set(keys, await deleteExternalServices(name));
    }
    catch (error: unknown) {
      setStatus(name, {
        message: t('external_services.delete_error.description', {
          message: getErrorMessage(error),
        }),
      });
    }
    finally {
      set(loading, false);
    }
  }

  function confirmDelete(name: string, postConfirmAction?: () => Promise<void> | void, confirmation: Partial<ConfirmationMessage> = {}): void {
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
  }

  watchImmediate(logged, async (isLogged) => {
    if (isLogged) {
      await load();
    }
    else {
      set(keys, undefined);
    }
  });

  return {
    actionStatus,
    confirmDelete,
    getApiKey,
    getName,
    keys: readonly(keys),
    load,
    loading: readonly(loading),
    save,
    useApiKey,
  };
});
