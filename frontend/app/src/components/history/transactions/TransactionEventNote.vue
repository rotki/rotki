<template>
  <div>
    <template v-for="(note, index) in formatNotes(notes, amount, asset)">
      <span
        v-if="note.type === 'address' || note.type === 'tx'"
        :key="index"
        class="d-inline-flex"
      >
        <hash-link
          :class="$style['address']"
          :text="note.address"
          :tx="note.type === 'tx'"
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
<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { bigNumberify } from '@/utils/bignumbers';
import { isValidEthAddress, isValidTxHash } from '@/utils/text';

defineProps({
  notes: { required: false, type: String, default: '' },
  amount: {
    required: false,
    type: BigNumber,
    default: null
  },
  asset: { required: false, type: String, default: '' }
});

enum NoteType {
  ADDRESS = 'address',
  TX = 'tx',
  AMOUNT = 'amount',
  WORD = 'word',
  URL = 'url'
}

type NoteFormat = {
  type: NoteType;
  word?: string;
  address?: string;
  amount?: BigNumber;
  asset?: string;
  url?: string;
};

const formatNotes = (
  notes: string,
  amount: BigNumber,
  assetId: string
): NoteFormat[] => {
  const { assetSymbol } = useAssetInfoRetrieval();

  const asset = get(assetSymbol(assetId));

  if (!notes) return [];

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
    if (isValidTxHash(word)) {
      formats.push({ type: NoteType.TX, address: word });
      return;
    }

    const isAmount =
      !isNaN(parseFloat(word)) &&
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
<style lang="scss" module>
.address {
  background: var(--v-rotki-light-grey-darken1);
  padding: 0 0.25rem 0 0.5rem;
  border-radius: 3rem;
  margin: 2px;
}
</style>
