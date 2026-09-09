import { findAddressKnownPrefix, truncateAddress } from '@/modules/core/common/display/truncate';

/**
 * The width one character takes in the label's font, in pixels.
 *
 * @remarks
 * Measured rather than derived. The label renders in a monospaced face, so one constant stands for
 * every character; a proportional font would need the text measured instead.
 */
const CHARACTER_WIDTH = 7.21;

/**
 * The label shortened to whatever fits the space it has.
 *
 * @remarks
 * The ellipsis and the address prefix (`0x`, an xpub prefix) are kept whole and charged against the
 * budget, so what remains is split evenly between the head and the tail. A width that fits the
 * whole label leaves it alone.
 *
 * A width too small to hold even the prefix and the ellipsis leaves the label alone, which covers
 * the element not having been measured yet: its container hides the overflow, so an unshortened
 * label is clipped rather than wrong. Truncating on that budget would ask for a negative number of
 * characters, which returns a string *longer* than the label it was given.
 *
 * @param label - the address or name to show
 * @param availableWidth - the space the label has, in pixels; zero means not yet measured
 * @returns the label, truncated only when it does not fit and there is room to say so
 */
export function truncateToWidth(label: string, availableWidth: number): string {
  const charDisplayLimit = Math.floor(availableWidth / CHARACTER_WIDTH);

  if (charDisplayLimit >= label.length)
    return label;

  const knownPrefix = findAddressKnownPrefix(label);
  const charactersWithinSpace = Math.floor((charDisplayLimit - knownPrefix.length - 3) / 2);

  if (charactersWithinSpace < 1)
    return label;

  return truncateAddress(label, charactersWithinSpace);
}
