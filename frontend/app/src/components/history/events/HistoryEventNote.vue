<script setup lang="ts">
import { type BigNumber, Blockchain } from '@rotki/common';
import { type NoteFormat, NoteType } from '@/composables/history/events/notes';
import type { ExplorerUrls } from '@/types/asset/asset-urls';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    notes?: string;
    amount?: BigNumber;
    asset?: string;
    chain?: string;
    noTxHash?: boolean;
    validatorIndex?: number;
    blockNumber?: number;
    counterparty?: string;
  }>(),
  {
    notes: '',
    amount: undefined,
    asset: '',
    chain: Blockchain.ETH,
    noTxHash: false,
    validatorIndex: undefined,
    blockNumber: undefined,
  },
);

const { notes, amount, asset, noTxHash, validatorIndex, blockNumber, counterparty } = toRefs(props);

const { formatNotes } = useHistoryEventNote();

const formattedNotes: ComputedRef<NoteFormat[]> = formatNotes({
  notes,
  amount,
  assetId: asset,
  noTxHash,
  validatorIndex,
  blockNumber,
  counterparty,
});

function isLinkType(t: any): t is keyof ExplorerUrls {
  return [NoteType.TX, NoteType.ADDRESS, NoteType.BLOCK].includes(t);
}
</script>

<template>
  <div
    v-bind="$attrs"
    class="inline-flex items-center gap-x-1 flex-wrap"
  >
    <template
      v-for="(note, index) in formattedNotes"
      :key="index"
    >
      <template v-if="note.type === NoteType.FLAG && note.countryCode">
        <Flag
          :iso="note.countryCode"
          class="mr-1"
        />
      </template>
      <template v-else-if="note.type === NoteType.WORD && note.word">
        <span :key="`span-${index}`">{{ note.word }}</span>
      </template>
      <HashLink
        v-else-if="note.showHashLink && isLinkType(note.type)"
        :key="index"
        class="inline-flex"
        :class="{
          [$style.address]: true,
          'pl-2': !note.showIcon,
        }"
        :text="note.address"
        :type="note.type"
        :chain="note.chain ?? chain"
        :show-icon="!!note.showIcon"
      />
      <AmountDisplay
        v-else-if="note.type === NoteType.AMOUNT && note.amount"
        :key="`${index}-amount`"
        :asset="note.asset"
        :value="note.amount"
      />
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
        {{ `${note.word} ` }}
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
