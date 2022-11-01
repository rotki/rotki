import { Blockchain } from '@rotki/common/lib/blockchain';
import { Ref } from 'vue';
import { GeneralAccountData } from '@/services/types-api';
import { RestChains } from '@/types/blockchain/chains';
import { removeTags } from '@/utils/tags';

export const useChainsAccountsStore = defineStore(
  'blockchain/accounts/chains',
  () => {
    const ksm: Ref<GeneralAccountData[]> = ref([]);
    const dot: Ref<GeneralAccountData[]> = ref([]);
    const avax: Ref<GeneralAccountData[]> = ref([]);

    const removeTag = (tag: string) => {
      set(ksm, removeTags(ksm, tag));
      set(dot, removeTags(dot, tag));
      set(avax, removeTags(avax, tag));
    };

    const update = (chain: RestChains, data: GeneralAccountData[]) => {
      if (chain === Blockchain.KSM) {
        set(ksm, data);
      } else if (chain === Blockchain.DOT) {
        set(dot, data);
      } else if (chain === Blockchain.AVAX) {
        set(avax, data);
      }
    };

    return {
      ksm,
      dot,
      avax,
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
