import { Blockchain } from '@rotki/common/lib/blockchain';
import { type ComputedRef, type Ref } from 'vue';
import { type GeneralAccountData } from '@/services/types-api';
import { type RestChains } from '@/types/blockchain/chains';
import { removeTags } from '@/utils/tags';

export const useChainsAccountsStore = defineStore(
  'blockchain/accounts/chains',
  () => {
    const ksm: Ref<GeneralAccountData[]> = ref([]);
    const dot: Ref<GeneralAccountData[]> = ref([]);
    const avax: Ref<GeneralAccountData[]> = ref([]);
    const optimism: Ref<GeneralAccountData[]> = ref([]);

    const removeTag = (tag: string) => {
      set(ksm, removeTags(ksm, tag));
      set(dot, removeTags(dot, tag));
      set(avax, removeTags(avax, tag));
      set(optimism, removeTags(optimism, tag));
    };

    const update = (chain: RestChains, data: GeneralAccountData[]) => {
      if (chain === Blockchain.KSM) {
        set(ksm, data);
      } else if (chain === Blockchain.DOT) {
        set(dot, data);
      } else if (chain === Blockchain.AVAX) {
        set(avax, data);
      } else if (chain === Blockchain.OPTIMISM) {
        set(optimism, data);
      }
    };

    const optimismAddresses: ComputedRef<string[]> = computed(() => {
      return get(optimism).map(({ address }) => address);
    });

    return {
      ksm,
      dot,
      avax,
      optimism,
      optimismAddresses,
      update,
      removeTag
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useChainsAccountsStore, import.meta.hot)
  );
}
