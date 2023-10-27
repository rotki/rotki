<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type AssetMovement } from '@/types/history/asset-movements';
import { isValidTxHash } from '@/utils/text';

const props = defineProps<{
  item: AssetMovement;
}>();

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
  <span class="flex flex-col pt-1">
    <span v-if="item.address" class="flex flex-row">
      <span class="mr-1 font-medium"> {{ t('common.address') }}: </span>
      <HashLink :text="item.address" :chain="chain" full-address no-link />
    </span>
    <span v-if="item.transactionId" class="flex flex-row mt-1">
      <span class="mr-1 font-medium"> {{ t('common.tx') }}: </span>
      <HashLink
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
