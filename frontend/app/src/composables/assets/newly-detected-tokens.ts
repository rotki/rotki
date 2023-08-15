import { type NewDetectedToken } from '@/types/websocket-messages';

const MAX_SIZE = 500;

const createStorage = (username: string): Ref<NewDetectedToken[]> =>
  useLocalStorage(`rotki.newly_detected_tokens.${username}`, []);

export const useNewlyDetectedTokens = createSharedComposable(() => {
  let internalTokens: Ref<NewDetectedToken[]> = ref([]);

  const initTokens = (username: string): void => {
    internalTokens = createStorage(username);
  };

  const clearInternalTokens = () => {
    set(internalTokens, []);
  };

  const ignoredAssetStore = useIgnoredAssetsStore();
  const { addIgnoredAsset } = ignoredAssetStore;

  const addNewDetectedToken = (data: NewDetectedToken): boolean => {
    if (data.isIgnored) {
      addIgnoredAsset(data.tokenIdentifier);
      return false;
    }

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
    return tokenIndex === -1;
  };

  const removeNewDetectedTokens = (tokensToRemove: string[]) => {
    const filtered = get(internalTokens).filter(
      item => !tokensToRemove.includes(item.tokenIdentifier)
    );

    set(internalTokens, filtered);
  };

  const tokens: ComputedRef<NewDetectedToken[]> = computed(() =>
    get(internalTokens)
  );

  return {
    tokens,
    initTokens,
    removeNewDetectedTokens,
    clearInternalTokens,
    addNewDetectedToken
  };
});
