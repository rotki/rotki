// Public suffixes list
// Source: https://github.com/lupomontero/psl/blob/c445ac9c9ebe7a795335e11b1d4831c1bed8dbb2/data/rules.json
import psl from '@/data/psl.json';

export const pslSuffixes: Set<string> = new Set(psl.psl);
