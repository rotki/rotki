<script setup lang="ts">
import type { ExplorerUrls } from '@/types/asset/asset-urls';
import Flag from '@/components/common/Flag.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import { type NoteFormat, NoteType, useHistoryEventNote } from '@/composables/history/events/notes';
import HashLink from '@/modules/common/links/HashLink.vue';
import { type BigNumber, Blockchain } from '@rotki/common';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    notes?: string;
    amount?: BigNumber | BigNumber[];
    asset?: string;
    chain?: string;
    noTxHash?: boolean;
    validatorIndex?: number;
    blockNumber?: number;
    counterparty?: string;
  }>(),
  {
    amount: undefined,
    asset: '',
    blockNumber: undefined,
    chain: Blockchain.ETH,
    notes: '',
    noTxHash: false,
    validatorIndex: undefined,
  },
);

const { amount, asset, blockNumber, counterparty, notes, noTxHash, validatorIndex } = toRefs(props);

const { formatNotes } = useHistoryEventNote();

const formattedNotes: ComputedRef<NoteFormat[]> = formatNotes({
  amount,
  assetId: asset,
  blockNumber,
  counterparty,
  notes,
  noTxHash,
  validatorIndex,
});

function isLinkType(t: any): t is keyof ExplorerUrls {
  return [NoteType.TX, NoteType.ADDRESS, NoteType.BLOCK].includes(t);
}
</script>

<template>
  <div
    v-bind="$attrs"
    class="inline"
  >
    <template
      v-for="(note, index) in formattedNotes"
      :key="index"
    >
      <template v-if="note.type === NoteType.FLAG && note.countryCode">
        <Flag
          :iso="note.countryCode"
          class="mx-1 rounded-sm"
        />
      </template>
      <template v-else-if="note.type === NoteType.WORD && note.word">
        {{ ` ${note.word} ` }}
      </template>
      <HashLink
        v-else-if="note.showHashLink && note.address && isLinkType(note.type)"
        :key="index"
        class="inline-flex pl-2"
        :class="{
          [$style.address]: true,
        }"
        :text="note.address"
        :type="note.type"
        :location="note.chain ?? chain"
      />
      <template v-else-if="note.type === NoteType.AMOUNT">
        <AmountDisplay
          v-if="note.amount"
          :key="`${index}-amount`"
          no-truncate
          :asset="note.asset"
          :value="note.amount"
          :resolution-options="{
            collectionParent: false,
          }"
        />
        <AmountDisplay
          v-else
          :key="`${index}-amount-1`"
          no-truncate
          :value="note.amount"
        />
      </template>
      <ExternalLink
        v-else-if="note.type === NoteType.URL && note.url"
        :key="`${index}-link`"
        :url="note.url"
        class="text-wrap hover:underline"
        :text="note.word"
        color="primary"
        custom
      />
      <template v-else>
        {{ ` ${note.word} ` }}
      </template>
    </template>
  </div>
</template>

<style lang="scss" module>
.address {
  @apply align-middle bg-rui-grey-300 pr-1 rounded-full m-0.5;
}

:global(.dark) {
  .address {
    @apply bg-rui-grey-800;
  }
}
</style>
