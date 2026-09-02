import psl from '@/modules/core/common/psl.json';

/**
 * The public suffix list, as a set so membership is a single lookup.
 *
 * @see https://github.com/lupomontero/psl/blob/c445ac9c9ebe7a795335e11b1d4831c1bed8dbb2/data/rules.json
 */
export const pslSuffixes: Set<string> = new Set(psl.psl);
