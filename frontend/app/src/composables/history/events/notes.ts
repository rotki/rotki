import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useScramble } from '@/composables/scramble';
import { uniqueStrings } from '@/utils/data';
import { type BigNumber, bigNumberify, Blockchain, isEvmIdentifier, isValidEthAddress, isValidTxHash } from '@rotki/common';

export const NoteType = {
  ADDRESS: 'address',
  AMOUNT: 'amount',
  BLOCK: 'block',
  FLAG: 'flag',
  TX: 'transaction',
  URL: 'url',
  WORD: 'word',
} as const;

export type NoteType = (typeof NoteType)[keyof typeof NoteType];

export interface NoteFormat {
  type: NoteType;
  word?: string;
  address?: string;
  amount?: BigNumber;
  asset?: string;
  url?: string;
  chain?: Blockchain;
  showHashLink?: boolean;
  countryCode?: string;
}

interface FormatNoteParams {
  notes: MaybeRef<string>;
  amount?: MaybeRef<BigNumber | undefined>;
  assetId?: MaybeRef<string>;
  noTxHash?: MaybeRef<boolean>;
  validatorIndex?: MaybeRef<number | undefined>;
  blockNumber?: MaybeRef<number | undefined>;
  counterparty?: MaybeRef<string | undefined>;
}

interface UseHistoryEventsNoteReturn {
  formatNotes: (params: FormatNoteParams) => ComputedRef<NoteFormat[]>;
}

export function useHistoryEventNote(): UseHistoryEventsNoteReturn {
  const { assetSymbol } = useAssetInfoRetrieval();
  const { scrambleData, scrambleIdentifier } = useScramble();

  function separateByPunctuation(word: string): string[] {
    // Use a regular expression to find trailing characters
    const trailingMatch = word.match(/\.+$/);

    // Extract the trailing characters if they exist, otherwise set to an empty string
    const trailingChars = trailingMatch ? trailingMatch[0] : '';

    // Remove the trailing characters from the original word
    const mainPart = word.substring(0, word.length - trailingChars.length);

    // Construct the result array
    const result = [];
    if (mainPart)
      result.push(mainPart);
    if (trailingChars)
      result.push(trailingChars);

    return result;
  }

  function findAndScrambleIBAN(notes: string): string {
    // Regex pattern to match IBANs in the text
    const ibanPattern = /\b[A-Z]{2}\d{2}(?:\s?[\dA-Z]{1,4}){1,7}\b/g;

    // Find all IBAN matches
    const ibanMatches = notes.match(ibanPattern);

    if (ibanMatches) {
      ibanMatches.filter(uniqueStrings)?.forEach((iban) => {
        const ibanGroupingPattern = /^([A-Z]{2})(\d{2})\s?([\d\sA-Z]{1,30})$/;
        const groups = iban.match(ibanGroupingPattern);

        if (groups) {
          const checkDigit = groups[2];
          const scrambledCheckDigit = scrambleIdentifier(checkDigit, 10, 99);

          // Extract and split the BBAN part into individual groups by spaces
          const bban = groups[3].trim();
          const bbanGroups = bban.split(/\s+/);

          const scrambledBbanNumbers = bbanGroups.map(item => scrambleIdentifier(item, 1000, 9999));
          const formatted = `XX${scrambledCheckDigit} ${scrambledBbanNumbers.join(' ')}`;

          notes = notes.replace(new RegExp(iban, 'g'), formatted);
        }
      });
    }

    return notes;
  }

  /**
   * Merges sequential "WORD" type entries in an array of NoteFormat objects.
   *
   * @param {NoteFormat[]} formats - The array of existing NoteFormat objects.
   * @param {NoteFormat} current - The current NoteFormat object to be added or merged.
   * @returns {NoteFormat[]} The updated array of NoteFormat objects.
   *
   * This function checks if the last entry in the 'formats' array and the 'current' entry
   * are both of type 'WORD'. If so, it merges the 'current' word with the last entry's word.
   * Otherwise, it simply adds the 'current' entry to the 'formats' array.
   *
   * This is done to avoid rendering each word as a single text node.
   */
  const mergeSequentialWords = (formats: NoteFormat[], current: NoteFormat): NoteFormat[] => {
    const lastFormatEntry = formats.at(-1);
    if (!lastFormatEntry) {
      formats.push(current);
      return formats;
    }
    if (current.type === NoteType.WORD && lastFormatEntry.type === NoteType.WORD) {
      lastFormatEntry.word += ` ${current.word}`;
      return formats;
    }
    else {
      formats.push(current);
      return formats;
    }
  };

  const formatNotes = ({
    amount,
    assetId,
    blockNumber,
    counterparty,
    notes,
    noTxHash,
    validatorIndex,
  }: FormatNoteParams): ComputedRef<NoteFormat[]> => computed<NoteFormat[]>(() => {
    const asset = get(assetSymbol(assetId, {
      collectionParent: false,
    }));

    let notesVal = get(notes);
    if (!notesVal)
      return [];

    const formats: NoteFormat[] = [];
    let skip = false;

    const counterpartyVal = get(counterparty);

    // Check if we need to scramble IBAN
    if (get(scrambleData) && counterpartyVal === 'monerium')
      notesVal = findAndScrambleIBAN(notesVal);

    const words = notesVal
      .replace(/(\d),(?=\d{3}(?!\d))/g, '$1_COMMA_')
      .split(/[\s,]+/)
      .map(word => word.replace(/_COMMA_/g, ','));

    const assetWords = asset ? asset.split(/\s+/) : [];
    const processedWords: string[] = [];

    for (let i = 0; i < words.length; i++) {
      if (asset && i + assetWords.length <= words.length
        && words.slice(i, i + assetWords.length).join(' ') === asset) {
        processedWords.push(asset);
        i += assetWords.length - 1;
      }
      else {
        processedWords.push(words[i]);
      }
    }

    processedWords.forEach((wordItem, index) => {
      if (skip) {
        skip = false;
        return;
      }

      const split = separateByPunctuation(wordItem);

      if (split.length === 0)
        return;

      const word = split[0];

      const putBackPunctuation = (): void => {
        if (!split[1])
          return;

        formats.push({
          type: NoteType.WORD,
          word: split[1],
        });
      };

      // Check if the word is ETH address
      if (isValidEthAddress(word)) {
        formats.push({
          address: word,
          showHashLink: true,
          type: NoteType.ADDRESS,
        });
        return putBackPunctuation();
      }

      // Check if the word is Tx Hash
      if (isValidTxHash(word) && !get(noTxHash)) {
        formats.push({
          address: word,
          showHashLink: true,
          type: NoteType.TX,
        });
        return putBackPunctuation();
      }

      // Check if the word is ETH2 Validator Index
      if (get(validatorIndex)?.toString() === word) {
        formats.push({
          address: word,
          chain: Blockchain.ETH2,
          showHashLink: true,
          type: NoteType.ADDRESS,
        });
        return putBackPunctuation();
      }

      // Check if the word is Block Number
      if (get(blockNumber)?.toString() === word) {
        formats.push({
          address: word,
          showHashLink: true,
          type: NoteType.BLOCK,
        });
        return putBackPunctuation();
      }

      const amountVal = get(amount);
      const wordUsed = word.replace(/(\d),(?=\d{3}(?!\d))/g, '$1');

      const isAmount = amountVal
        && !isNaN(Number.parseFloat(wordUsed))
        && bigNumberify(wordUsed).eq(amountVal)
        && amountVal.gt(0);

      if (isAmount) {
        const isAsset = index < processedWords.length - 1
          && processedWords[index + 1] === asset;

        formats.push({
          amount: amountVal,
          asset: isAsset ? get(assetId) : undefined,
          type: NoteType.AMOUNT,
        });

        if (isAsset)
          skip = true;

        return putBackPunctuation();
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
            url,
            word: text,
          });

          return putBackPunctuation();
        }
      }

      // Check if the word is URL
      const urlRegex = /^(https?:\/\/.+)$/;

      if (urlRegex.test(word)) {
        formats.push({
          type: NoteType.URL,
          url: word,
          word,
        });

        return putBackPunctuation();
      }

      if (isEvmIdentifier(word)) {
        const symbol = get(assetSymbol(word));
        if (symbol) {
          formats.push({
            type: NoteType.WORD,
            word: symbol,
          });
          return putBackPunctuation();
        }
      }
      // Check if the word is a country flag
      const countryFlagRegex = /:country:([A-Z]{2}):/;
      const countryFlagMatch = word.match(countryFlagRegex);
      if (countryFlagMatch && counterpartyVal === 'gnosis_pay') {
        formats.push({
          countryCode: countryFlagMatch[1]?.toLowerCase(),
          type: NoteType.FLAG,
        });
        return putBackPunctuation();
      }

      formats.push({ type: NoteType.WORD, word: split.join('') });
    });

    return formats.reduce(mergeSequentialWords, new Array<NoteFormat>());
  });

  return {
    formatNotes,
  };
}
