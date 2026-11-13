/** What a filter does to the pairs it describes: keeps them all, drops them, or keeps only them. */
export const InteractionFilterMode = {
  EXCLUDE: 'exclude',
  INCLUDE: 'include',
  ONLY: 'only',
} as const;

export type InteractionFilterMode = typeof InteractionFilterMode[keyof typeof InteractionFilterMode];

/** Whether a pair that has (or lacks) the filtered trait passes `mode`. */
export function passesMode(mode: InteractionFilterMode, hasTrait: boolean): boolean {
  if (mode === InteractionFilterMode.ONLY)
    return hasTrait;
  if (mode === InteractionFilterMode.EXCLUDE)
    return !hasTrait;
  return true;
}
