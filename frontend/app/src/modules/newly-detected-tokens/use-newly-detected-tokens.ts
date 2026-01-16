import type { MaybeRef, Ref } from 'vue';
import type { NewDetectedToken, NewDetectedTokenInput, NewDetectedTokenKind, NewDetectedTokensRequestPayload } from './types';
import type { Collection } from '@/types/collection';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useNewlyDetectedTokensDb } from './use-newly-detected-tokens-db';

interface UseNewlyDetectedTokensReturn {
  addNewDetectedToken: (data: NewDetectedTokenInput) => Promise<boolean>;
  clearInternalTokens: () => Promise<void>;
  count: () => Promise<number>;
  getAllIdentifiers: (tokenKind?: NewDetectedTokenKind) => Promise<string[]>;
  getData: (payload: MaybeRef<NewDetectedTokensRequestPayload>) => Promise<Collection<NewDetectedToken>>;
  isReady: Ref<boolean>;
  removeNewDetectedTokens: (tokensToRemove: string[]) => Promise<void>;
}

export const useNewlyDetectedTokens = createSharedComposable((): UseNewlyDetectedTokensReturn => {
  const ignoredAssetStore = useIgnoredAssetsStore();
  const { ignoredAssets } = storeToRefs(ignoredAssetStore);
  const { addIgnoredAsset } = ignoredAssetStore;

  const settingsStore = useFrontendSettingsStore();
  const { notifyNewNfts } = storeToRefs(settingsStore);

  const {
    addToken,
    clearAll,
    count,
    getAllIdentifiers,
    getData,
    isReady,
    removeTokens,
  } = useNewlyDetectedTokensDb();

  async function addNewDetectedToken(data: NewDetectedTokenInput): Promise<boolean> {
    if (!get(notifyNewNfts) && data.tokenIdentifier.includes('erc721'))
      return false;

    if (data.isIgnored) {
      addIgnoredAsset(data.tokenIdentifier);
      return false;
    }

    return addToken(data);
  }

  async function removeNewDetectedTokens(tokensToRemove: string[]): Promise<void> {
    return removeTokens(tokensToRemove);
  }

  async function clearInternalTokens(): Promise<void> {
    return clearAll();
  }

  watch(ignoredAssets, async (value, oldValue): Promise<void> => {
    const ignoredItems = value.filter(x => !oldValue.includes(x));
    if (ignoredItems.length > 0) {
      await removeNewDetectedTokens(ignoredItems);
    }
  });

  return {
    addNewDetectedToken,
    clearInternalTokens,
    count,
    getAllIdentifiers,
    getData,
    isReady,
    removeNewDetectedTokens,
  };
});
