<template>
  <span class="d-flex flex-column pt-1">
    <span v-if="item.address" class="d-flex flex-row">
      <span class="mr-1 font-weight-medium"> {{ tc('common.address') }}: </span>
      <hash-link :text="item.address" :chain="chain" full-address />
    </span>
    <span v-if="item.transactionId" class="d-flex flex-row mt-1">
      <span class="mr-1 font-weight-medium"> {{ tc('common.tx') }}: </span>
      <hash-link
        v-if="isValidTxHash(transactionId)"
        :text="transactionId"
        :chain="chain"
        tx
        full-address
      />
      <span v-else>{{ item.transactionId ?? '' }}</span>
    </span>
  </span>
</template>
<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { PropType } from 'vue';
import HashLink from '@/components/helper/HashLink.vue';
import { AssetMovement } from '@/types/history/movements';
import { isEvmIdentifier } from '@/utils/assets';
import { isValidTxHash } from '@/utils/text';

const props = defineProps({
  item: { required: true, type: Object as PropType<AssetMovement> }
});

const { item } = toRefs(props);

const { tc } = useI18n();

// TODO: make it so that the chains are retrieved from the backend
const chain = computed<Blockchain>(() => {
  if (
    get(isEvmIdentifier(get(item).asset)) ||
    get(item).asset === Blockchain.ETH
  ) {
    return Blockchain.ETH;
  }
  return get(item).asset as Blockchain;
});

const transactionId = computed<string>(() => {
  const { transactionId } = get(item);
  if (!transactionId) return '';

  if (get(chain) !== Blockchain.ETH) {
    return transactionId;
  }

  return transactionId.startsWith('0x') ? transactionId : `0x${transactionId}`;
});
</script>
