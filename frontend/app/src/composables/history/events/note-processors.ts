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
import { type NoteFormat, NoteType } from './notes';

// Word processor types
export interface WordProcessorContext {
  word: string;
  index: number;
  processedWords: string[];
  asset?: string;
  assetId?: string;
  amountArr: BigNumber[];
  validatorIndices: string[];
  blockNumber?: number;
  counterparty?: string;
  noTxRef?: boolean;
  shouldFormatAllAmount: boolean;
  getCleanWord: (word: string) => string;
  getAssetSymbol: (id: string) => string;
}

export interface WordProcessorResult {
  format: NoteFormat;
  skipNext?: boolean;
}

export type WordProcessor = (ctx: WordProcessorContext) => WordProcessorResult | undefined;

// Pure word processors - each handles one type of word format
const processAddress: WordProcessor = ({ word }) => {
  const isValidBch = isValidBchAddress(word);
  if (!isValidEthAddress(word) && !isValidBtcAddress(word) && !isValidBch && !isValidSolanaAddress(word))
    return undefined;

  return {
    format: {
      address: isValidBch ? word.replace(/^bitcoincash:/, '') : word,
      showHashLink: true,
      type: NoteType.ADDRESS,
    },
  };
};

const processTxHash: WordProcessor = ({ word, noTxRef }) => {
  if (!isValidEvmTxHash(word))
    return undefined;

  return {
    format: {
      address: word,
      showHashLink: true,
      showCopyOnly: noTxRef,
      type: NoteType.TX,
    },
  };
};

const processValidatorIndex: WordProcessor = ({ word, validatorIndices }) => {
  if (!validatorIndices.includes(word))
    return undefined;

  return {
    format: {
      address: word,
      chain: Blockchain.ETH2,
      showHashLink: true,
      type: NoteType.ADDRESS,
    },
  };
};

const processBlockNumber: WordProcessor = ({ word, blockNumber }) => {
  if (blockNumber?.toString() !== word)
    return undefined;

  return {
    format: {
      address: word,
      showHashLink: true,
      type: NoteType.BLOCK,
    },
  };
};

const processAmount: WordProcessor = ({
  word,
  index,
  processedWords,
  asset,
  assetId,
  amountArr,
  shouldFormatAllAmount,
  getCleanWord,
}) => {
  const wordUsed = word.replace(/(\d),(?=\d{3}(?!\d))/g, '$1');
  const isAmount = (amountArr.length > 0 || shouldFormatAllAmount) && !isNaN(parseFloat(wordUsed));

  if (!isAmount)
    return undefined;

  const bigNumber = bigNumberify(wordUsed);
  const isIncluded = amountArr.some(item => item.eq(bigNumber)) || shouldFormatAllAmount;

  if (!isIncluded || !bigNumber.gt(0))
    return undefined;

  const isAsset = index < processedWords.length - 1 && getCleanWord(processedWords[index + 1]) === asset;

  return {
    format: {
      amount: bigNumber,
      asset: isAsset ? assetId : undefined,
      type: NoteType.AMOUNT,
    },
    skipNext: isAsset,
  };
};

const MARKDOWN_LINK_REGEX = /^\[(.+)]\((<?https?:\/\/.+>?)\)$/;

const processMarkdownLink: WordProcessor = ({ word }) => {
  const match = word.match(MARKDOWN_LINK_REGEX);
  if (!match)
    return undefined;

  const text = match[1];
  let url = match[2];

  if (!text || !url)
    return undefined;

  url = url.replace(/^<+/, '').replace(/>+$/, '');
  return {
    format: {
      type: NoteType.URL,
      url,
      word: text,
    },
  };
};

const URL_REGEX = /^(https?:\/\/.+)$/;

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname;
  }
  catch {
    return url;
  }
}

const processUrl: WordProcessor = ({ word }) => {
  if (!URL_REGEX.test(word))
    return undefined;

  return {
    format: {
      type: NoteType.URL,
      url: word,
      word: extractDomain(word),
    },
  };
};

const processEvmIdentifier: WordProcessor = ({ word, getAssetSymbol }) => {
  if (!isEvmIdentifier(word))
    return undefined;

  const symbol = getAssetSymbol(word);
  if (!symbol)
    return undefined;

  return {
    format: {
      type: NoteType.WORD,
      word: symbol,
    },
  };
};

const processGnosisPay: WordProcessor = ({ word, counterparty }) => {
  if (counterparty !== 'gnosis_pay')
    return undefined;

  const countryFlagMatch = word.match(/:country:([A-Z]{2}):/);
  if (countryFlagMatch) {
    return {
      format: {
        countryCode: countryFlagMatch[1]?.toLowerCase(),
        type: NoteType.FLAG,
      },
    };
  }

  const merchantCodeMatch = word.match(/:merchant_code:(\d+):/);
  if (merchantCodeMatch) {
    return {
      format: {
        merchantCode: merchantCodeMatch[1],
        type: NoteType.MERCHANT_CODE,
      },
    };
  }

  return undefined;
};

// Ordered by expected frequency for better performance
export const WORD_PROCESSORS: WordProcessor[] = [
  processAddress,
  processTxHash,
  processValidatorIndex,
  processBlockNumber,
  processAmount,
  processMarkdownLink,
  processUrl,
  processEvmIdentifier,
  processGnosisPay,
];
