import { isValidEthAddress } from '@rotki/common';
import { uniqueStrings } from '@/modules/core/common/data/data';

function filterAddressesFromWords(words: string[]): string[] {
  return words.filter(uniqueStrings).filter(isValidEthAddress);
}

export function getEthAddressesFromText(notes: string): string[] {
  return filterAddressesFromWords(notes.split(/\s|\\n/));
}
