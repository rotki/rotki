import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRef } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useScramble } from '@/composables/scramble';
import { arrayify } from '@/utils/array';
import { uniqueStrings } from '@/utils/data';
import { WORD_PROCESSORS, type WordProcessorContext, type WordProcessorResult } from './note-processors';

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
  chain?: string;
  showHashLink?: boolean;
  showCopyOnly?: boolean;
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
    const result: string[] = [];
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

  function mergeSequentialWords(formats: NoteFormat[], current: NoteFormat): NoteFormat[] {
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
  }

  function buildValidatorIndices(
    validatorIndex: number | undefined,
    extraData: Record<string, any> | undefined,
  ): string[] {
    return [
      validatorIndex?.toString(),
      extraData && 'sourceValidatorIndex' in extraData ? extraData.sourceValidatorIndex.toString() : undefined,
      extraData && 'targetValidatorIndex' in extraData ? extraData.targetValidatorIndex.toString() : undefined,
    ].filter((v): v is string => v !== undefined);
  }

  function tokenizeNotes(notesVal: string, asset: string | undefined): string[] {
    const words = notesVal
      .replace(/(\d),(?=\d{3}(?!\d))/g, '$1_COMMA_')
      .split(/[\s,]+/)
      .map(word => word.replace(/_COMMA_/g, ','));

    if (!asset)
      return words;

    // Merge multi-word asset names back together
    const assetWords = asset.split(/\s+/);
    const processedWords: string[] = [];

    for (let i = 0; i < words.length; i++) {
      if (i + assetWords.length <= words.length && words.slice(i, i + assetWords.length).join(' ') === asset) {
        processedWords.push(asset);
        i += assetWords.length - 1;
      }
      else {
        processedWords.push(words[i]);
      }
    }

    return processedWords;
  }

  function processWord(
    ctx: Omit<WordProcessorContext, 'word' | 'index'>,
    word: string,
    index: number,
  ): WordProcessorResult | undefined {
    for (const processor of WORD_PROCESSORS) {
      const result = processor({ ...ctx, word, index });
      if (result)
        return result;
    }
    return undefined;
  }

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
    const asset = get(assetSymbol(assetId, { collectionParent: false }));
    const extraDataVal = get(extraData);

    let notesVal = get(notes);
    if (!notesVal)
      return [];

    const counterpartyVal = get(counterparty);

    // Scramble IBAN for monerium
    if (get(scrambleData) && counterpartyVal === 'monerium')
      notesVal = findAndScrambleIBAN(notesVal);

    const processedWords = tokenizeNotes(notesVal, asset);
    const formats: NoteFormat[] = [];
    let skip = false;

    // Build context values once, outside the loop
    const amountVal = get(amount);
    const ctx: Omit<WordProcessorContext, 'word' | 'index'> = {
      processedWords,
      asset: asset || undefined,
      assetId: get(assetId),
      amountArr: amountVal ? arrayify(amountVal) : [],
      validatorIndices: buildValidatorIndices(get(validatorIndex), extraDataVal),
      blockNumber: get(blockNumber),
      counterparty: counterpartyVal,
      noTxRef: get(noTxRef),
      shouldFormatAllAmount: counterpartyVal === 'gnosis_pay',
      getCleanWord,
      getAssetSymbol: (id: string) => get(assetSymbol(id)),
    };

    for (const [index, wordItem] of processedWords.entries()) {
      if (skip) {
        skip = false;
        continue;
      }

      const split = separateByPunctuation(wordItem);
      if (split.length === 0)
        continue;

      const { leading, trailing, word } = parsePunctuation(split);
      const result = processWord(ctx, word, index);

      if (leading)
        formats.push({ type: NoteType.WORD, word: leading });

      if (result) {
        formats.push(result.format);
        if (result.skipNext)
          skip = true;
      }
      else {
        formats.push({ type: NoteType.WORD, word });
      }

      if (trailing)
        formats.push({ type: NoteType.WORD, word: trailing });
    }

    return formats.reduce(mergeSequentialWords, new Array<NoteFormat>());
  });

  return {
    formatNotes,
  };
}
