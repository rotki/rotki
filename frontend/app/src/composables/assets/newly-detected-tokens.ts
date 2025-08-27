import type { NewDetectedToken } from '@/modules/messaging/types';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const MAX_SIZE = 500;
const NEWLY_DETECTED_TOKENS_PREFIX = 'rotki.newly_detected_tokens.';

function createStorage(identifier: string): Ref<NewDetectedToken[]> {
  return useLocalStorage(`${NEWLY_DETECTED_TOKENS_PREFIX}${identifier}`, []);
}

export const useNewlyDetectedTokens = createSharedComposable(() => {
  let internalTokens = ref<NewDetectedToken[]>([]);

  const ignoredAssetStore = useIgnoredAssetsStore();
  const { ignoredAssets } = storeToRefs(ignoredAssetStore);
  const { addIgnoredAsset } = ignoredAssetStore;
  const loggedUserIdentifier = useLoggedUserIdentifier();
  const settingsStore = useFrontendSettingsStore();
  const { notifyNewNfts } = storeToRefs(settingsStore);

  const tokens = computed<NewDetectedToken[]>(() => get(internalTokens));

  const clearInternalTokens = (): void => {
    set(internalTokens, []);
  };

  const addNewDetectedToken = (data: NewDetectedToken): boolean => {
    if (!get(notifyNewNfts) && data.tokenIdentifier.includes('erc721')) {
      return false;
    }

    if (data.isIgnored) {
      addIgnoredAsset(data.tokenIdentifier);
      return false;
    }

    const tokenList = [...get(internalTokens)];
    const tokenIndex = tokenList.findIndex(({ tokenIdentifier }) => tokenIdentifier === data.tokenIdentifier);

    if (tokenIndex === -1)
      tokenList.push(data);
    else
      tokenList.splice(tokenIndex, 1, data);

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
    if (identifier) {
      internalTokens = createStorage(identifier);
    }
    else {
      internalTokens = ref<NewDetectedToken[]>([]);
    }
  }, { immediate: true });

  return {
    addNewDetectedToken,
    clearInternalTokens,
    removeNewDetectedTokens,
    tokens,
  };
});
