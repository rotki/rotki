import { useScramble } from '@/modules/settings/use-scramble';
import { type Activity, type ActivityText, resolveText } from '@/modules/task-center/core/types';

interface UseActivityLabelReturn {
  /**
   * The subtitle, translated, with any address in it scrambled while privacy mode is on. Resolved at
   * render rather than at submit time, so a language change updates work already in flight.
   */
  subtitleOf: (activity: Activity) => string | undefined;
  /**
   * What a row calls the activity: what it acts on when nested under a parent, its title otherwise.
   *
   * @remarks
   * Under a parent, the siblings share the title and the verb ("Refreshing Ethereum", "Refreshing
   * Gnosis" and so on under "Refreshing 21 chains"), so only the thing each acts on tells them apart. That is
   * read from the subtitle's params, most specific first (see {@link IDENTITY_PARAMS}); a subtitle
   * with none of them is shown whole. So is one whose identity is its parent's: a chain's decode
   * names only the chain, and under that chain's row it would read as the chain again.
   */
  labelOf: (activity: Activity, nested: boolean, parent?: Activity) => string;
}

/**
 * The subtitle params that name what an activity acts on, most specific first: an account under a
 * chain carries both `address` and `chain`, and the address is what differs between siblings.
 */
const IDENTITY_PARAMS = ['address', 'xpub', 'validator', 'chain', 'location', 'exchange', 'bank', 'source', 'protocol', 'asset'] as const;

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

  /**
   * The name of what an activity acts on, from its subtitle params, with its `account` beside it
   * when there is one ("Kraken (main)"), since two accounts on one exchange are otherwise the same.
   */
  function identityOf(activity: Activity): string | undefined {
    const subtitle = displaySubtitle(activity.subtitle);
    if (subtitle === undefined || typeof subtitle === 'string')
      return undefined;

    const params = subtitle.params ?? {};
    const key = IDENTITY_PARAMS.find(name => typeof params[name] === 'string' && params[name] !== '');
    if (key === undefined)
      return undefined;

    const { account } = params;
    return typeof account === 'string' && account !== '' ? `${String(params[key])} (${account})` : String(params[key]);
  }

  function labelOf(activity: Activity, nested: boolean, parent?: Activity): string {
    if (!nested)
      return activity.title;

    const identity = identityOf(activity);
    const sharesParentIdentity = identity !== undefined && parent !== undefined && identity === identityOf(parent);
    return (sharesParentIdentity ? undefined : identity) ?? subtitleOf(activity) ?? activity.title;
  }

  return { labelOf, subtitleOf };
}
