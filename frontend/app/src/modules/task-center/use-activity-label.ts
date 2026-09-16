import { useScramble } from '@/modules/settings/use-scramble';
import { type Activity, type ActivityText, resolveText } from '@/modules/task-center/core/types';

interface UseActivityLabelReturn {
  /**
   * The subtitle, translated, with any address in it scrambled while privacy mode is on. Resolved at
   * render rather than at submit time, so a language change updates work already in flight.
   */
  subtitleOf: (activity: Activity) => string | undefined;
  /**
   * What a row calls the activity: its subtitle when nested under a parent, its title otherwise.
   *
   * @remarks
   * Under a parent the subtitle is the identity. Every chain and account in one flow carries the
   * same title, so a child of "History refresh" reads as "Ethereum" rather than "Transaction sync /
   * Ethereum", where only the second half distinguishes it from its siblings.
   */
  labelOf: (activity: Activity, nested: boolean) => string;
}

/** Resolves activity text for display, in the current language and privacy mode. */
export function useActivityLabel(): UseActivityLabelReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { scrambleAddress } = useScramble();

  /**
   * Rewrites a param that may hold one address or several.
   *
   * @remarks
   * A batch joins several addresses into one string, so each is scrambled separately and the
   * separators put back verbatim. `scrambleAddress` returns its input unchanged while privacy mode
   * is off, so this needs no condition of its own.
   *
   * @param value - a subtitle param, which is only rewritten when it is a string
   * @returns the value with each address replaced
   */
  function scrambleAddresses(value: unknown): unknown {
    if (typeof value !== 'string')
      return value;

    return value
      .split(/([\s,]+)/)
      .map(part => (/^[\s,]*$/.test(part) ? part : scrambleAddress(part)))
      .join('');
  }

  /**
   * Scrambles the address param before {@link resolveText} interpolates it; afterwards nothing can
   * tell the address apart from the wording around it. Every producer that carries an address
   * passes it as `address`, so that is the one key rewritten.
   */
  function displaySubtitle(value: ActivityText | undefined): ActivityText | undefined {
    if (value === undefined || typeof value === 'string' || value.params?.address === undefined)
      return value;

    return { ...value, params: { ...value.params, address: scrambleAddresses(value.params.address) } };
  }

  function subtitleOf(activity: Activity): string | undefined {
    return resolveText(t, displaySubtitle(activity.subtitle));
  }

  function labelOf(activity: Activity, nested: boolean): string {
    return nested ? subtitleOf(activity) ?? activity.title : activity.title;
  }

  return { labelOf, subtitleOf };
}
