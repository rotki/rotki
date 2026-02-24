import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';

interface UseProxyProtocolReturn {
  isProxy: ComputedRef<boolean>;
  parsedProtocol: ComputedRef<string>;
  proxyAddress: ComputedRef<string | undefined>;
}

export function useProxyProtocol(protocol: MaybeRefOrGetter<string>): UseProxyProtocolReturn {
  const isProxy = computed<boolean>(() => toValue(protocol).startsWith('proxy:'));

  const parsedProtocol = computed<string>(() => {
    const value = toValue(protocol);
    if (get(isProxy)) {
      const parts = value.split(':');
      return parts[1] ?? value;
    }
    return value;
  });

  const proxyAddress = computed<string | undefined>(() => {
    if (!get(isProxy))
      return undefined;

    const parts = toValue(protocol).split(':');
    return parts[2];
  });

  return {
    isProxy,
    parsedProtocol,
    proxyAddress,
  };
}
