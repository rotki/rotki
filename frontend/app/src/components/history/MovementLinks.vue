<template>
  <span class="d-flex flex-column pt-1">
    <span v-if="item.address" class="d-flex flex-row">
      <span class="mr-1 font-weight-medium">
        {{ $tc('common.address') }}:
      </span>
      <hash-link :text="item.address" :chain="chain" full-address />
    </span>
    <span v-if="item.transactionId" class="d-flex flex-row mt-1">
      <span class="mr-1 font-weight-medium"> {{ $tc('common.tx') }}: </span>
      <hash-link :text="transactionId" :chain="chain" tx full-address />
    </span>
  </span>
</template>
<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import HashLink from '@/components/helper/HashLink.vue';
import { AssetMovement } from '@/services/history/types';
import { useAssetInfoRetrieval } from '@/store/assets';

export default defineComponent({
  name: 'MovementLinks',
  components: { HashLink },
  props: {
    item: { required: true, type: Object as PropType<AssetMovement> }
  },
  setup(props) {
    const { item } = toRefs(props);

    const { isEthereumToken } = useAssetInfoRetrieval();

    const chain = computed<string>(() => {
      if (
        get(isEthereumToken(get(item).asset)) ||
        get(item).asset === Blockchain.ETH
      ) {
        return Blockchain.ETH;
      }
      return get(item).asset;
    });

    const transactionId = computed<string>(() => {
      const { transactionId } = get(item);
      if (!transactionId) return '';

      if (get(chain) !== Blockchain.ETH) {
        return transactionId;
      }

      return transactionId.startsWith('0x')
        ? transactionId
        : `0x${transactionId}`;
    });

    return {
      transactionId,
      chain
    };
  }
});
</script>
