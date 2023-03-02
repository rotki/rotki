<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { bigNumberify } from '@/utils/bignumbers';
import { isValidEthAddress, isValidTxHash } from '@/utils/text';

withDefaults(
  defineProps<{
    notes?: string;
    amount?: BigNumber | null;
    asset?: string;
    chain?: Blockchain;
    noTxHash?: boolean;
  }>(),
  {
    notes: '',
    amount: null,
    asset: '',
    chain: Blockchain.ETH,
    noTxHash: false
  }
);

enum NoteType {
  ADDRESS = 'address',
  TX = 'tx',
  AMOUNT = 'amount',
  WORD = 'word',
  URL = 'url'
}

interface NoteFormat {
  type: NoteType;
  word?: string;
  address?: string;
  amount?: BigNumber;
  asset?: string;
  url?: string;
}

const formatNotes = (
  notes: string,
  amount: BigNumber | null,
  assetId: string,
  noTxHash: boolean
): NoteFormat[] => {
  const { assetSymbol } = useAssetInfoRetrievalStore();

  const asset = get(assetSymbol(assetId));

  if (!notes) {
    return [];
  }

  const formats: NoteFormat[] = [];
  let skip = false;

  // label each word from notes whether it is an address or not
  const words = notes.split(/\s/);

  words.forEach((word, index) => {
    if (skip) {
      skip = false;
      return;
    }

    // Check if the word is ETH address
    if (isValidEthAddress(word)) {
      formats.push({ type: NoteType.ADDRESS, address: word });
      return;
    }

    // Check if the word is Tx Hash
    if (isValidTxHash(word) && !noTxHash) {
      formats.push({ type: NoteType.TX, address: word });
      return;
    }

    const isAmount =
      amount &&
      !isNaN(Number.parseFloat(word)) &&
      bigNumberify(word).eq(amount) &&
      amount.gt(0) &&
      index < words.length - 1 &&
      words[index + 1] === asset;

    if (isAmount) {
      formats.push({ type: NoteType.AMOUNT, amount, asset: assetId });
      skip = true;
      return;
    }

    // Check if the word is Markdown link format
    const markdownLinkRegex = /^\[(.+)]\((<?https?:\/\/.+>?)\)$/;
    const markdownLinkMatch = word.match(markdownLinkRegex);

    if (markdownLinkMatch) {
      const text = markdownLinkMatch[1];
      let url = markdownLinkMatch[2];

      if (text && url) {
        url = url.replace(/^<+/, '').replace(/>+$/, '');

        formats.push({
          type: NoteType.URL,
          word: text,
          url
        });

        return;
      }
    }

    // Check if the word is URL
    const urlRegex = /^(https?:\/\/.+)$/;

    if (urlRegex.test(word)) {
      formats.push({
        type: NoteType.URL,
        word,
        url: word
      });

      return;
    }

    formats.push({ type: NoteType.WORD, word });
  });

  return formats;
};
</script>
<template>
  <div>
    <template
      v-for="(note, index) in formatNotes(notes, amount, asset, noTxHash)"
    >
      <span
        v-if="note.type === 'address' || note.type === 'tx'"
        :key="index"
        :class="$style.address"
        class="d-inline-flex"
      >
        <hash-link
          :class="{
            [$style['address__content']]: true,
            'pl-2': note.type === 'tx'
          }"
          :text="note.address"
          :tx="note.type === 'tx'"
          :chain="chain"
        />
      </span>
      <span v-else-if="note.type === 'amount'" :key="index">
        <amount-display :asset="note.asset" :value="note.amount" />
      </span>
      <span v-else-if="note.type === 'url' && note.url" :key="index">
        <external-link :url="note.url">{{ note.word }}</external-link>
      </span>
      <span v-else :key="index">
        {{ note.word }}
      </span>
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
