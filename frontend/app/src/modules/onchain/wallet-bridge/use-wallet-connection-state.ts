import { createSharedComposable, set } from '@vueuse/core';
import { ref, type Ref } from 'vue';
import { logger } from '@/utils/logging';

interface WalletConnectionStateComposable {
  isRequestingAccounts: Readonly<Ref<boolean>>;
  setRequestingAccounts: (isRequesting: boolean) => void;
  trackAccountsRequest: <T>(promise: Promise<T>) => Promise<T>;
}

function createWalletConnectionState(): WalletConnectionStateComposable {
  const isRequestingAccounts = ref<boolean>(false);

  const setRequestingAccounts = (isRequesting: boolean): void => {
    set(isRequestingAccounts, isRequesting);
    logger.debug(`Account request state changed: ${isRequesting ? 'started' : 'finished'}`);
  };

  const trackAccountsRequest = async <T>(promise: Promise<T>): Promise<T> => {
    setRequestingAccounts(true);
    try {
      return await promise;
    }
    finally {
      setRequestingAccounts(false);
    }
  };

  return {
    isRequestingAccounts: readonly(isRequestingAccounts),
    setRequestingAccounts,
    trackAccountsRequest,
  };
}

export const useWalletConnectionState = createSharedComposable(createWalletConnectionState);
