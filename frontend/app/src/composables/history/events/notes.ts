import { type BigNumber, Blockchain } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';

export const NoteType = {
  ADDRESS: 'address',
  TX: 'transaction',
  BLOCK: 'block',
  AMOUNT: 'amount',
  WORD: 'word',
  URL: 'url',
  FLAG: 'flag',
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
  showIcon?: boolean;
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

  const formatNotes = ({
    notes,
    amount,
    assetId,
    noTxHash,
    validatorIndex,
    blockNumber,
    counterparty,
  }: FormatNoteParams): ComputedRef<NoteFormat[]> => computed<NoteFormat[]>(() => {
    const asset = get(assetSymbol(assetId));

    let notesVal = get(notes);
    if (!notesVal)
      return [];

    const formats: NoteFormat[] = [];
    let skip = false;

    const counterpartyVal = get(counterparty);

    // Check if we need to scramble IBAN
    if (get(scrambleData) && counterpartyVal === 'monerium')
      notesVal = findAndScrambleIBAN(notesVal);

    // label each word from notes whether it is an address or not
    const words = notesVal.split(/[\s,]+/);

    words.forEach((wordItem, index) => {
      if (skip) {
        skip = false;
        return;
      }

      const splitted = separateByPunctuation(wordItem);

      if (splitted.length === 0)
        return;

      const word = splitted[0];

      const putBackPunctuation = (): void => {
        if (!splitted[1])
          return;

        formats.push({
          type: NoteType.WORD,
          word: splitted[1],
        });
      };

      // Check if the word is ETH address
      if (isValidEthAddress(word)) {
        formats.push({
          type: NoteType.ADDRESS,
          address: word,
          showIcon: true,
          showHashLink: true,
        });
        return putBackPunctuation();
      }

      // Check if the word is Tx Hash
      if (isValidTxHash(word) && !get(noTxHash)) {
        formats.push({
          type: NoteType.TX,
          address: word,
          showHashLink: true,
        });
        return putBackPunctuation();
      }

      // Check if the word is ETH2 Validator Index
      if (get(validatorIndex)?.toString() === word) {
        formats.push({
          type: NoteType.ADDRESS,
          address: word,
          chain: Blockchain.ETH2,
          showHashLink: true,
        });
        return putBackPunctuation();
      }

      // Check if the word is Block Number
      if (get(blockNumber)?.toString() === word) {
        formats.push({
          type: NoteType.BLOCK,
          address: word,
          showHashLink: true,
        });
        return putBackPunctuation();
      }

      const amountVal = get(amount);

      const isAmount = amountVal
        && !isNaN(Number.parseFloat(word))
        && bigNumberify(word).eq(amountVal)
        && amountVal.gt(0)
        && index < words.length - 1
        && words[index + 1] === asset;

      if (isAmount) {
        formats.push({
          type: NoteType.AMOUNT,
          amount: amountVal,
          asset: get(assetId),
        });
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
            word: text,
            url,
          });

          return putBackPunctuation();
        }
      }

      // Check if the word is URL
      const urlRegex = /^(https?:\/\/.+)$/;

      if (urlRegex.test(word)) {
        formats.push({
          type: NoteType.URL,
          word,
          url: word,
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
          type: NoteType.FLAG,
          countryCode: countryFlagMatch[1]?.toLowerCase(),
        });
        return putBackPunctuation();
      }

      formats.push({ type: NoteType.WORD, word: splitted.join('') });
    });

    return formats;
  });

  return {
    formatNotes,
  };
}
