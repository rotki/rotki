import { type ComputedRef, type Ref } from 'vue';
import { type NewDetectedToken } from '@/types/websocket-messages';

const MAX_SIZE = 500;

const createStorage = (username: string): Ref<NewDetectedToken[]> => {
  return useLocalStorage(`rotki.newly_detected_tokens.${username}`, []);
};

export const useNewlyDetectedTokens = createSharedComposable(() => {
  let internalTokens: Ref<NewDetectedToken[]> = ref([]);

  const initTokens = (username: string): void => {
    internalTokens = createStorage(username);
  };

  const clearInternalTokens = () => {
    set(internalTokens, []);
  };

  const addNewDetectedToken = (data: NewDetectedToken) => {
    const tokenList = [...get(internalTokens)];
    const tokenIndex = tokenList.findIndex(
      ({ tokenIdentifier }) => tokenIdentifier === data.tokenIdentifier
    );
    if (tokenIndex === -1) {
      tokenList.push(data);
    } else {
      tokenList.splice(tokenIndex, 1, data);
    }
    set(internalTokens, tokenList.slice(-MAX_SIZE));
  };

  const removeNewDetectedTokens = (tokensToRemove: string[]) => {
    const filtered = get(internalTokens).filter(
      item => !tokensToRemove.includes(item.tokenIdentifier)
    );

    set(internalTokens, filtered);
  };

  const tokens: ComputedRef<NewDetectedToken[]> = computed(() => {
    return get(internalTokens);
  });

  return {
    tokens,
    initTokens,
    removeNewDetectedTokens,
    clearInternalTokens,
    addNewDetectedToken
  };
});
