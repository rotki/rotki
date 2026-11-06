import type { Ref } from 'vue';
import { isErr, type Result } from 'plainfp/result';

/**
 * A failure named for the strip that shows it.
 *
 * @remarks
 * The fields are named after `FailureStrip`'s props and bound one by one
 * (`:title="x.title" :failure="x.failure"`). A holder that needs more, such as an id or what to
 * retry, keeps it beside the failure rather than inside it, so the failure stays exactly what a strip
 * shows.
 */
export interface NamedFailure {
  readonly title: string;
  /** The error itself, or a string already worded; the strip words it with `useFailureMessage`. */
  readonly failure: unknown;
}

export interface FailureSlot {
  /** The last failure reported, until the next attempt clears it. */
  failure: Readonly<Ref<NamedFailure | undefined>>;
  report: (title: string, failure: unknown) => void;
  clear: () => void;
  /**
   * Clears the slot, runs the action, and keeps its failure under `title`.
   *
   * @remarks
   * The failure is what the action throws, or the error of an `Err` it resolves to; an `Ok` or
   * nothing leaves the slot empty. Swallows the throw: the slot is where it goes. An action whose
   * failure is neither, such as a `false`, returns it as an `Err`.
   */
  run: (title: string, action: () => Promise<void | Result<unknown, unknown>>) => Promise<void>;
}

/**
 * Holds the one failure a surface names at a time, so a new attempt replaces the last.
 */
export function useFailureSlot(): FailureSlot {
  const failure = shallowRef<NamedFailure>();

  function report(title: string, error: unknown): void {
    set(failure, { failure: error, title });
  }

  function clear(): void {
    set(failure, undefined);
  }

  async function run(title: string, action: () => Promise<void | Result<unknown, unknown>>): Promise<void> {
    clear();
    try {
      const outcome = await action();
      if (outcome !== undefined && isErr(outcome))
        report(title, outcome.error);
    }
    catch (error: unknown) {
      report(title, error);
    }
  }

  return {
    clear,
    failure: shallowReadonly(failure),
    report,
    run,
  };
}
