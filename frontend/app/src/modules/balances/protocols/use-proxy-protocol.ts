import { get } from '@vueuse/core';
import { computed, type ComputedRef, type MaybeRef } from 'vue';

interface UseProxyProtocolReturn {
  isProxy: ComputedRef<boolean>;
  parsedProtocol: ComputedRef<string>;
  proxyAddress: ComputedRef<string | undefined>;
}

export function useProxyProtocol(protocol: MaybeRef<string>): UseProxyProtocolReturn {
  const isProxy = computed<boolean>(() => get(protocol).startsWith('proxy:'));

  const parsedProtocol = computed<string>(() => {
    const value = get(protocol);
    if (get(isProxy)) {
      const parts = value.split(':');
      return parts[1] ?? value;
    }
    return value;
  });

  const proxyAddress = computed<string | undefined>(() => {
    if (!get(isProxy))
      return undefined;

    const parts = get(protocol).split(':');
    return parts[2];
  });

  return {
    isProxy,
    parsedProtocol,
    proxyAddress,
  };
}
