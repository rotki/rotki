import type { EvmTokensRecord } from '@/modules/balances/types/balances';

type Tokens = Record<string, EvmTokensRecord>;

export const useTokenDetectionStore = defineStore('blockchain/tokens', () => {
  const tokensState = shallowRef<Tokens>({});
  const massDetecting = shallowRef<string>();

  const setState = (chain: string, data: EvmTokensRecord): void => {
    const currentTokens: Tokens = { ...get(tokensState) };
    set(tokensState, {
      ...currentTokens,
      [chain]: {
        ...currentTokens[chain],
        ...data,
      },
    });
  };

  const setMassDetecting = (value: string | undefined): void => {
    set(massDetecting, value);
  };

  return {
    massDetecting,
    setMassDetecting,
    setState,
    tokensState,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useTokenDetectionStore, import.meta.hot));
