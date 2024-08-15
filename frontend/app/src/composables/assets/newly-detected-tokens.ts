import type { NewDetectedToken } from '@/types/websocket-messages';

const MAX_SIZE = 500;

function createStorage(identifier: string): Ref<NewDetectedToken[]> {
  return useLocalStorage(`rotki.newly_detected_tokens.${identifier}`, []);
}

export const useNewlyDetectedTokens = createSharedComposable(() => {
  let internalTokens = ref<NewDetectedToken[]>([]);

  const ignoredAssetStore = useIgnoredAssetsStore();
  const { ignoredAssets } = storeToRefs(ignoredAssetStore);
  const { addIgnoredAsset } = ignoredAssetStore;
  const loggedUserIdentifier = useLoggedUserIdentifier();

  const tokens = computed<NewDetectedToken[]>(() => get(internalTokens));

  const clearInternalTokens = (): void => {
    set(internalTokens, []);
  };

  const addNewDetectedToken = (data: NewDetectedToken): boolean => {
    if (data.isIgnored) {
      addIgnoredAsset(data.tokenIdentifier);
      return false;
    }

    const tokenList = [...get(internalTokens)];
    const tokenIndex = tokenList.findIndex(({ tokenIdentifier }) => tokenIdentifier === data.tokenIdentifier);

    if (tokenIndex === -1)
      tokenList.push(data);
    else tokenList.splice(tokenIndex, 1, data);

    set(internalTokens, tokenList.slice(-MAX_SIZE));
    return tokenIndex === -1;
  };

  const removeNewDetectedTokens = (tokensToRemove: string[]): void => {
    set(internalTokens, get(internalTokens).filter(item => !tokensToRemove.includes(item.tokenIdentifier)));
  };

  watch(ignoredAssets, (value, oldValue): void => {
    const ignoredItems = value.filter(x => !oldValue.includes(x));
    removeNewDetectedTokens(ignoredItems);
  });

  watch(loggedUserIdentifier, (identifier): void => {
    if (identifier)
      internalTokens = createStorage(identifier);
    else
      internalTokens = ref<NewDetectedToken[]>([]);
  }, { immediate: true });

  return {
    tokens,
    removeNewDetectedTokens,
    clearInternalTokens,
    addNewDetectedToken,
  };
});
