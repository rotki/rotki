<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type PropType } from 'vue';
import { type AssetMovement } from '@/types/history/asset-movements';
import { isValidTxHash } from '@/utils/text';

const props = defineProps({
  item: { required: true, type: Object as PropType<AssetMovement> }
});

const { item } = toRefs(props);

const { t } = useI18n();

// TODO: make it so that the chains are retrieved from the backend
const chain = computed<Blockchain>(() => {
  const assetInLowerCase = get(item).asset.toLowerCase();
  if (
    get(isEvmIdentifier(get(item).asset)) ||
    assetInLowerCase === Blockchain.ETH
  ) {
    return Blockchain.ETH;
  }
  return assetInLowerCase as Blockchain;
});

const transactionId = computed<string>(() => {
  const { transactionId } = get(item);
  if (!transactionId) {
    return '';
  }

  if (get(chain) !== Blockchain.ETH) {
    return transactionId;
  }

  return transactionId.startsWith('0x') ? transactionId : `0x${transactionId}`;
});
</script>

<template>
  <span class="d-flex flex-column pt-1">
    <span v-if="item.address" class="d-flex flex-row">
      <span class="mr-1 font-weight-medium"> {{ t('common.address') }}: </span>
      <hash-link :text="item.address" :chain="chain" full-address no-link />
    </span>
    <span v-if="item.transactionId" class="d-flex flex-row mt-1">
      <span class="mr-1 font-weight-medium"> {{ t('common.tx') }}: </span>
      <hash-link
        v-if="isValidTxHash(transactionId)"
        :text="transactionId"
        :chain="chain"
        type="transaction"
        full-address
        no-link
      />
      <span v-else>{{ item.transactionId ?? '' }}</span>
    </span>
  </span>
</template>
