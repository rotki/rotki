<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type ComputedRef } from 'vue';
import { type NoteFormat, NoteType } from '@/composables/history/events/notes';
import { type ExplorerUrls } from '@/types/asset/asset-urls';

defineOptions({
  inheritAttrs: false
});

const props = withDefaults(
  defineProps<{
    notes?: string;
    amount?: BigNumber;
    asset?: string;
    chain?: Blockchain;
    noTxHash?: boolean;
    validatorIndex?: number;
    blockNumber?: number;
  }>(),
  {
    notes: '',
    amount: undefined,
    asset: '',
    chain: Blockchain.ETH,
    noTxHash: false,
    validatorIndex: undefined,
    blockNumber: undefined
  }
);

const { notes, amount, asset, noTxHash, validatorIndex, blockNumber } =
  toRefs(props);

const { formatNotes } = useHistoryEventNote();

const formattedNotes: ComputedRef<NoteFormat[]> = formatNotes({
  notes,
  amount,
  assetId: asset,
  noTxHash,
  validatorIndex,
  blockNumber
});

const css = useCssModule();

const isLinkType = (t: any): t is keyof ExplorerUrls =>
  [NoteType.TX, NoteType.ADDRESS, NoteType.BLOCK].includes(t);
</script>

<template>
  <div>
    <template v-for="(note, index) in formattedNotes">
      <HashLink
        v-if="note.showHashLink && isLinkType(note.type)"
        :key="index"
        class="inline-flex"
        :class="{
          [css['address__content']]: true,
          'pl-2': !note.showIcon,
          [css.address]: true
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
      >
        {{ note.word }}
      </ExternalLink>

      <template v-else>
        {{ note.word }}
      </template>
    </template>
  </div>
</template>

<style lang="scss" module>
.address {
  vertical-align: middle;

  &__content {
    background: var(--v-rotki-light-grey-darken1);
    padding-right: 0.25rem;
    border-radius: 3rem;
    margin: 2px;
  }
}
</style>
