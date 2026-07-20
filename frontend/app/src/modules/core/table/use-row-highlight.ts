interface UseRowHighlightOptions {
  /** How long the highlight stays before it fades, in milliseconds. */
  duration?: number;
  /** Class applied to every row so the highlight fades smoothly on/off. */
  baseClass?: string;
  /** Class applied only to the currently highlighted row. */
  highlightClass?: string;
}

interface UseRowHighlightReturn<T> {
  highlight: (item: T) => void;
  isHighlighted: (item: T) => boolean;
  rowClass: (item: T) => string;
}

/**
 * Transiently highlights a single table row (e.g. one that was just added) so
 * the eye lands on it, then fades it out. Rows are identified by `keyOf`, so it
 * works with any row shape and any table that accepts a per-row class function.
 */
export function useRowHighlight<T>(
  keyOf: (item: T) => string,
  options: UseRowHighlightOptions = {},
): UseRowHighlightReturn<T> {
  const {
    baseClass = 'transition-colors duration-1000',
    duration = 2500,
    highlightClass = 'bg-rui-primary/[0.08]',
  } = options;

  const highlighted = ref<string>();

  const { start, stop } = useTimeoutFn(() => {
    set(highlighted, undefined);
  }, duration, { immediate: false });

  function highlight(item: T): void {
    stop();
    set(highlighted, keyOf(item));
    start();
  }

  function isHighlighted(item: T): boolean {
    return isDefined(highlighted) && get(highlighted) === keyOf(item);
  }

  function rowClass(item: T): string {
    return isHighlighted(item) ? `${baseClass} ${highlightClass}` : baseClass;
  }

  return { highlight, isHighlighted, rowClass };
}
