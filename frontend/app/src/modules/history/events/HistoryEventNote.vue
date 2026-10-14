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

interface NoteDisplay {
  note: NoteFormat;
  /** The word just before an amount, kept on the amount's line. */
  lead?: string;
}

/** The words of a run before an amount, if the amount can take the last one with it. */
function wordsBefore(previous: NoteDisplay | undefined, note: NoteFormat): string | undefined {
  if (note.type !== NoteType.AMOUNT || !note.amount || previous?.note.type !== NoteType.WORD)
    return undefined;
  return previous.note.word?.trimEnd() || undefined;
}

/**
 * Moves the last word before each amount onto the amount, so a line break can never leave a word
 * like "to" alone at a line's end with its amount on the next one.
 */
const displayNotes = computed<NoteDisplay[]>(() => {
  const display: NoteDisplay[] = [];
  for (const note of get(formattedNotes)) {
    const previous = display.at(-1);
    const words = wordsBefore(previous, note);
    if (!previous || !words) {
      display.push({ note });
      continue;
    }
    const cut = words.lastIndexOf(' ');
    if (cut === -1)
      display.pop();
    else
      previous.note = { ...previous.note, word: words.slice(0, cut) };
    display.push({ lead: words.slice(cut + 1), note });
  }
  return display;
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
      v-for="({ note, lead }, index) in displayNotes"
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
        class="inline-flex align-middle bg-rui-grey-300/50 dark:bg-rui-grey-800/50 pr-1 rounded-full m-0.5"
        :class="{
          'pl-2': isLinkTypeWithoutImage(note.type, note.chain ?? chain),
        }"
        :text="note.address"
        :type="note.type"
        :location="note.chain ?? chain"
        :display-mode="note.showCopyOnly ? 'copy' : 'default'"
      />
      <span
        v-else-if="note.type === NoteType.AMOUNT"
        :class="{ 'whitespace-nowrap': lead }"
      >
        <template v-if="lead">
          {{ ` ${lead} ` }}
        </template>
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
      </span>
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
