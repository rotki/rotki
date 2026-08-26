/**
 * A short, stable digest of a set of strings — for activity ids whose identity is "which things",
 * not "which order they arrived in".
 *
 * Order-independent by construction (the input is sorted first), so two callers naming the same
 * subjects dedup onto one activity however each of them happened to build its list.
 *
 * FNV-1a over 32 bits: a compact id part, not a collision-proof hash. That is the right trade
 * for an activity id, where a collision costs a shared row and never data.
 */
export function setDigest(values: readonly string[]): string {
  let hash = 0x811C9DC5;
  for (const value of [...values].sort()) {
    for (let index = 0; index < value.length; index++) {
      hash = Math.imul(hash ^ value.charCodeAt(index), 0x01000193);
    }
    // Fold the separator too, so ['ab','c'] and ['a','bc'] cannot land on the same digest.
    hash = Math.imul(hash ^ 0x2C, 0x01000193);
  }
  return (hash >>> 0).toString(36);
}
