/** The one export `e2e-coverage-report.ts` uses; the package ships no typings. */
declare module '@bcoe/v8-coverage' {
  import type { Profiler } from 'node:inspector';

  /** Merges results of the same script, or `undefined` for an empty list. */
  export function mergeScriptCovs(scriptCovs: Profiler.ScriptCoverage[]): Profiler.ScriptCoverage | undefined;
}
