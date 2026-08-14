<script setup lang="ts">
import type { ExplorerUrls } from '@/modules/assets/asset-urls';
import { Blockchain } from '@rotki/common';
import { AssetAmountDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import { type HistoryEventNoteContext, type NoteFormat, NoteType, useHistoryEventNote } from '@/modules/history/events/use-history-event-note';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import Flag from '@/modules/shell/components/Flag.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import MerchantIcon from '@/modules/shell/components/MerchantIcon.vue';

defineOptions({
  inheritAttrs: false,
});

const {
  chain = Blockchain.ETH,
  context,
  notes = '',
} = defineProps<{
  notes?: string;
  /** The event the note describes, as far as resolving its placeholders needs it. */
  context?: HistoryEventNoteContext;
  /** Chain the explorer links resolve against; unlike `context` it is a display concern. */
  chain?: string;
}>();

const { formatNotes } = useHistoryEventNote();

const asset = computed<string>(() => context?.asset ?? '');

const formattedNotes: ComputedRef<NoteFormat[]> = formatNotes({
  amount: () => context?.amount,
  assetId: asset,
  blockNumber: () => context?.blockNumber,
  counterparty: () => context?.counterparty,
  extraData: () => context?.extraData,
  notes: () => notes,
  noTxRef: () => context?.noTxRef ?? false,
  validatorIndex: () => context?.validatorIndex,
});

function isLinkType(t: any): t is keyof ExplorerUrls {
  return [NoteType.TX, NoteType.ADDRESS, NoteType.BLOCK].includes(t);
}

function isLinkTypeWithoutImage(t: any, chain: string): t is keyof ExplorerUrls {
  return [NoteType.TX, NoteType.BLOCK].includes(t) || chain === Blockchain.ETH2;
}
</script>

<template>
  <div
    v-bind="$attrs"
    data-testid="event-notes"
    class="notes-content text-sm text-rui-text-secondary leading-relaxed"
  >
    <template
      v-for="(note, index) in formattedNotes"
      :key="index"
    >
      <template v-if="note.type === NoteType.FLAG && note.countryCode">
        <Flag
          :iso="note.countryCode"
          class="mx-1"
        />
      </template>
      <template v-else-if="note.type === NoteType.MERCHANT_CODE && note.merchantCode">
        <MerchantIcon
          :code="note.merchantCode"
          class="mx-0.5"
        />
      </template>
      <template v-else-if="note.type === NoteType.WORD && note.word">
        {{ ` ${note.word} ` }}
      </template>
      <HashLink
        v-else-if="note.showHashLink && note.address && isLinkType(note.type)"
        :key="index"
        class="inline-flex align-middle bg-rui-grey-300 dark:bg-rui-grey-800 pr-1 rounded-full m-0.5"
        :class="{
          'pl-2': isLinkTypeWithoutImage(note.type, note.chain ?? chain),
        }"
        :text="note.address"
        :type="note.type"
        :location="note.chain ?? chain"
        :display-mode="note.showCopyOnly ? 'copy' : 'default'"
      />
      <template v-else-if="note.type === NoteType.AMOUNT">
        <AssetAmountDisplay
          v-if="note.amount && note.asset"
          :key="`${index}-amount`"
          :asset="note.asset"
          :amount="note.amount"
          no-truncate
          no-collection-parent
        />
        <ValueDisplay
          v-else-if="note.amount"
          :key="`${index}-amount-1`"
          no-truncate
          :value="note.amount"
        />
      </template>
      <ExternalLink
        v-else-if="note.type === NoteType.URL && note.url"
        :key="`${index}-link`"
        :url="note.url"
        :title="note.url"
        class="text-wrap hover:underline"
        :text="note.word"
        color="primary"
        custom
        confirm
      />
      <template v-else>
        {{ ` ${note.word} ` }}
      </template>
    </template>
  </div>
</template>
