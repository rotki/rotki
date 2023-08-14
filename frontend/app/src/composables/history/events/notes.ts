import { type MaybeRef } from '@vueuse/core';
import { type BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';

export enum NoteType {
  ADDRESS = 'address',
  TX = 'transaction',
  BLOCK = 'block',
  AMOUNT = 'amount',
  WORD = 'word',
  URL = 'url'
}

export interface NoteFormat {
  type: NoteType;
  word?: string;
  address?: string;
  amount?: BigNumber;
  asset?: string;
  url?: string;
  chain?: Blockchain;
  showIcon?: boolean;
  showHashLink?: boolean;
}

export const useHistoryEventNote = () => {
  const { assetSymbol } = useAssetInfoRetrieval();

  const formatNotes = ({
    notes,
    amount,
    assetId,
    noTxHash,
    validatorIndex,
    blockNumber
  }: {
    notes: MaybeRef<string>;
    amount?: MaybeRef<BigNumber | null>;
    assetId?: MaybeRef<string>;
    noTxHash?: MaybeRef<boolean>;
    validatorIndex?: MaybeRef<number | null>;
    blockNumber?: MaybeRef<number | null>;
  }): ComputedRef<NoteFormat[]> =>
    computed(() => {
      const asset = get(assetSymbol(assetId));

      const notesVal = get(notes);
      if (!notesVal) {
        return [];
      }

      const formats: NoteFormat[] = [];
      let skip = false;

      // label each word from notes whether it is an address or not
      const words = notesVal.split(/\s|,/);

      words.forEach((word, index) => {
        if (skip) {
          skip = false;
          return;
        }

        // Check if the word is ETH address
        if (isValidEthAddress(word)) {
          formats.push({
            type: NoteType.ADDRESS,
            address: word,
            showIcon: true,
            showHashLink: true
          });
          return;
        }

        // Check if the word is Tx Hash
        if (isValidTxHash(word) && !get(noTxHash)) {
          formats.push({
            type: NoteType.TX,
            address: word,
            showHashLink: true
          });
          return;
        }

        // Check if the word is ETH2 Validator Index
        if (get(validatorIndex)?.toString() === word) {
          formats.push({
            type: NoteType.ADDRESS,
            address: word,
            chain: Blockchain.ETH2,
            showHashLink: true
          });
          return;
        }

        // Check if the word is Block Number
        if (get(blockNumber)?.toString() === word) {
          formats.push({
            type: NoteType.BLOCK,
            address: word,
            showHashLink: true
          });
          return;
        }

        const amountVal = get(amount);

        const isAmount =
          amountVal &&
          !isNaN(Number.parseFloat(word)) &&
          bigNumberify(word).eq(amountVal) &&
          amountVal.gt(0) &&
          index < words.length - 1 &&
          words[index + 1] === asset;

        if (isAmount) {
          formats.push({
            type: NoteType.AMOUNT,
            amount: amountVal,
            asset: get(assetId)
          });
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
    });

  return {
    formatNotes
  };
};
