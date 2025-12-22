import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import {
  type BigNumber,
  bigNumberify,
  Blockchain,
  isEvmIdentifier,
  isValidBchAddress,
  isValidBtcAddress,
  isValidEthAddress,
  isValidEvmTxHash,
  isValidSolanaAddress,
} from '@rotki/common';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useScramble } from '@/composables/scramble';
import { arrayify } from '@/utils/array';
import { uniqueStrings } from '@/utils/data';

export const NoteType = {
  ADDRESS: 'address',
  AMOUNT: 'amount',
  BLOCK: 'block',
  FLAG: 'flag',
  MERCHANT_CODE: 'merchant_code',
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
  merchantCode?: string;
}

interface FormatNoteParams {
  notes: MaybeRef<string>;
  amount?: MaybeRef<BigNumber | BigNumber[] | undefined>;
  assetId?: MaybeRef<string>;
  noTxRef?: MaybeRef<boolean>;
  validatorIndex?: MaybeRef<number | undefined>;
  blockNumber?: MaybeRef<number | undefined>;
  counterparty?: MaybeRef<string | undefined>;
  extraData?: MaybeRef<Record<string, any> | undefined>;
}

interface UseHistoryEventsNoteReturn {
  formatNotes: (params: FormatNoteParams) => ComputedRef<NoteFormat[]>;
}

export function useHistoryEventNote(): UseHistoryEventsNoteReturn {
  const { assetSymbol } = useAssetInfoRetrieval();
  const { scrambleData, scrambleIdentifier } = useScramble();

  function separateByPunctuation(word: string): string[] {
    const result = [];
    const openParenMatch = word.match(/^\(/);
    const openParen = openParenMatch ? openParenMatch[0] : '';

    let remaining = openParen ? word.substring(1) : word;
    const closeParenMatch = remaining.match(/\)(?=\.*$)/);
    const closeParen = closeParenMatch ? ')' : '';

    if (closeParen) {
      const closeParenIndex = remaining.lastIndexOf(')');
      remaining = remaining.substring(0, closeParenIndex) + remaining.substring(closeParenIndex + 1);
    }

    const trailingMatch = remaining.match(/\.+$/);
    const trailingDots = trailingMatch ? trailingMatch[0] : '';
    const mainPart = remaining.substring(0, remaining.length - trailingDots.length);

    if (openParen)
      result.push(openParen);
    if (mainPart)
      result.push(mainPart);
    if (closeParen)
      result.push(closeParen);
    if (trailingDots)
      result.push(trailingDots);
    return result;
  }

  function parsePunctuation(split: string[]): { leading: string; trailing: string; word: string } {
    let word = '';
    let leading = '';
    let trailing = '';

    for (const part of split) {
      if (/^[().]+$/.test(part)) {
        if (!word)
          leading += part;
        else
          trailing += part;
      }
      else {
        word = part;
      }
    }

    return { leading, trailing, word };
  }

  function getCleanWord(wordWithPunctuation: string): string {
    const split = separateByPunctuation(wordWithPunctuation);
    return split.find(part => !/^[().]+$/.test(part)) || '';
  }

  function findAndScrambleIBAN(notes: string): string {
    const ibanPattern = /\b[A-Z]{2}\d{2}(?:\s?[\dA-Z]{1,4}){1,7}\b/g;
    const ibanMatches = notes.match(ibanPattern);
    if (ibanMatches) {
      ibanMatches.filter(uniqueStrings)?.forEach((iban) => {
        const groups = iban.match(/^([A-Z]{2})(\d{2})\s?([\d\sA-Z]{1,30})$/);
        if (groups) {
          const scrambledCheckDigit = scrambleIdentifier(groups[2], 10, 99);
          const bbanGroups = groups[3].trim().split(/\s+/);
          const scrambledBbanNumbers = bbanGroups.map(item => scrambleIdentifier(item, 1000, 9999));
          notes = notes.replace(new RegExp(iban, 'g'), `XX${scrambledCheckDigit} ${scrambledBbanNumbers.join(' ')}`);
        }
      });
    }
    return notes;
  }

  const mergeSequentialWords = (formats: NoteFormat[], current: NoteFormat): NoteFormat[] => {
    const lastFormatEntry = formats.at(-1);
    if (!lastFormatEntry) {
      formats.push(current);
      return formats;
    }
    if (current.type === NoteType.WORD && lastFormatEntry.type === NoteType.WORD) {
      const isClosingPunctuation = /^[!),.:;?]+$/.test(current.word || '');
      const separator = isClosingPunctuation ? '' : ' ';
      lastFormatEntry.word += `${separator}${current.word}`;
      return formats;
    }
    formats.push(current);
    return formats;
  };

  const formatNotes = ({
    amount,
    assetId,
    blockNumber,
    counterparty,
    extraData,
    notes,
    noTxRef,
    validatorIndex,
  }: FormatNoteParams): ComputedRef<NoteFormat[]> => computed<NoteFormat[]>(() => {
    const asset = get(assetSymbol(assetId, {
      collectionParent: false,
    }));

    const extraDataVal = get(extraData);

    let notesVal = get(notes);
    if (!notesVal)
      return [];

    const formats: NoteFormat[] = [];
    let skip = false;

    const counterpartyVal = get(counterparty);
    const isMonerium = counterpartyVal === 'monerium';
    const shouldFormatAllAmount = counterpartyVal === 'gnosis_pay';

    // Check if we need to scramble IBAN
    if (get(scrambleData) && isMonerium)
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

      const { leading: leadingPunctuation, trailing: trailingPunctuation, word } = parsePunctuation(split);

      const addLeadingPunctuation = (): void => {
        if (leadingPunctuation) {
          formats.push({ type: NoteType.WORD, word: leadingPunctuation });
        }
      };

      const addTrailingPunctuation = (): void => {
        if (trailingPunctuation) {
          formats.push({ type: NoteType.WORD, word: trailingPunctuation });
        }
      };

      const isValidBch = isValidBchAddress(word);

      if (isValidEthAddress(word) || isValidBtcAddress(word) || isValidBch || isValidSolanaAddress(word)) {
        addLeadingPunctuation();
        formats.push({
          address: isValidBch ? word.replace(/^bitcoincash:/, '') : word,
          showHashLink: true,
          type: NoteType.ADDRESS,
        });
        return addTrailingPunctuation();
      }

      // Check if the word is Tx Hash
      if (isValidEvmTxHash(word) && !get(noTxRef)) {
        addLeadingPunctuation();
        formats.push({
          address: word,
          showHashLink: true,
          type: NoteType.TX,
        });
        return addTrailingPunctuation();
      }

      const validatorIndices = [];
      const validatorIndexVal = get(validatorIndex);

      if (validatorIndexVal) {
        validatorIndices.push(validatorIndexVal.toString());
      }

      if (extraDataVal && 'sourceValidatorIndex' in extraDataVal) {
        validatorIndices.push(extraDataVal.sourceValidatorIndex.toString());
      }

      if (extraDataVal && 'targetValidatorIndex' in extraDataVal) {
        validatorIndices.push(extraDataVal.targetValidatorIndex.toString());
      }

      // Check if the word is ETH2 Validator Index
      if (validatorIndices.includes(word)) {
        addLeadingPunctuation();
        formats.push({
          address: word,
          chain: Blockchain.ETH2,
          showHashLink: true,
          type: NoteType.ADDRESS,
        });
        return addTrailingPunctuation();
      }

      // Check if the word is Block Number
      if (get(blockNumber)?.toString() === word) {
        addLeadingPunctuation();
        formats.push({
          address: word,
          showHashLink: true,
          type: NoteType.BLOCK,
        });
        return addTrailingPunctuation();
      }

      const amountVal = get(amount);
      const amountArr: BigNumber[] = amountVal ? arrayify(amountVal) : [];
      const wordUsed = word.replace(/(\d),(?=\d{3}(?!\d))/g, '$1');

      const isAmount = (amountArr.length > 0 || shouldFormatAllAmount)
        && !isNaN(parseFloat(wordUsed));

      if (isAmount) {
        const bigNumber = bigNumberify(wordUsed);
        const isIncluded = amountArr.some(item => item.eq(bigNumber)) || shouldFormatAllAmount;

        if (isIncluded && bigNumber.gt(0)) {
          // Check if next word (without punctuation) is the asset
          const isAsset = index < processedWords.length - 1
            && getCleanWord(processedWords[index + 1]) === asset;

          addLeadingPunctuation();
          formats.push({
            amount: bigNumber,
            asset: isAsset ? get(assetId) : undefined,
            type: NoteType.AMOUNT,
          });

          if (isAsset)
            skip = true;

          return addTrailingPunctuation();
        }
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

          addLeadingPunctuation();
          return addTrailingPunctuation();
        }
      }

      // Check if the word is URL
      const urlRegex = /^(https?:\/\/.+)$/;

      if (urlRegex.test(word)) {
        addLeadingPunctuation();
        formats.push({
          type: NoteType.URL,
          url: word,
          word,
        });

        return addTrailingPunctuation();
      }

      if (isEvmIdentifier(word)) {
        const symbol = get(assetSymbol(word));
        if (symbol) {
          formats.push({
            type: NoteType.WORD,
            word: symbol,
          });
          addLeadingPunctuation();
          return addTrailingPunctuation();
        }
      }

      // Check Gnosis Pay specific patterns (country flag and merchant code)
      if (counterpartyVal === 'gnosis_pay') {
        const countryFlagMatch = word.match(/:country:([A-Z]{2}):/);
        if (countryFlagMatch) {
          addLeadingPunctuation();
          formats.push({ countryCode: countryFlagMatch[1]?.toLowerCase(), type: NoteType.FLAG });
          return addTrailingPunctuation();
        }
        const merchantCodeMatch = word.match(/:merchant_code:(\d+):/);
        if (merchantCodeMatch) {
          addLeadingPunctuation();
          formats.push({ merchantCode: merchantCodeMatch[1], type: NoteType.MERCHANT_CODE });
          return addTrailingPunctuation();
        }
      }

      addLeadingPunctuation();
      formats.push({ type: NoteType.WORD, word });
      addTrailingPunctuation();
    });

    return formats.reduce(mergeSequentialWords, new Array<NoteFormat>());
  });

  return {
    formatNotes,
  };
}
