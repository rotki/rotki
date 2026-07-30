/**
 * Acronyms that must stay upper case in text that has been case-normalized for display.
 * Matched whole-word only, so `ethereum` is untouched.
 */
const ACRONYMS = /\b(?:evm|eth|nft|rpc|ens|csv|api)\b/gi;

/**
 * Restores acronym casing in an already human-readable string.
 *
 * Case normalizers work a word at a time and cannot know which words are acronyms, so
 * `toHumanReadable('evm swap event', 'sentence')` gives `Evm swap event`. Applying this after
 * gives `EVM swap event`. Cheaper than mapping every value to a hand-written label, and a value
 * the backend adds later is handled without a code change.
 */
export function capitalizeAcronyms(value: string): string {
  return value.replace(ACRONYMS, match => match.toUpperCase());
}
