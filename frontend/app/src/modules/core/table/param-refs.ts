import type { Ref, WritableComputedRef } from 'vue';
import type { LocationQuery, LocationQueryValue } from 'vue-router';
import type { ParamSource } from '@/modules/core/table/param-sources';
import { arrayify } from '@/modules/core/common/data/array';

/**
 * What can be handed back for one key: absent, a value, or a repeated value from the query, or the
 * already-typed value the pill bar's bag carries.
 */
type RawQueryValue = LocationQueryValue | LocationQueryValue[] | boolean | undefined;

/** The flat shape the pill bar's `params` model is written in. */
export type PillParams = Record<string, string | string[] | boolean>;

/**
 * One param key's directions, each closing over the ref it belongs to.
 *
 * Closures rather than the ref itself, so a spec can mix a `string[]` key with a `boolean` one
 * without erasing either type. The constructors below are the way in; nothing else builds this.
 */
export interface ParamRef {
  /** Writes the ref from what the query, or the bar's bag, carried for this key. */
  readonly read: (raw: RawQueryValue) => void;
  /** Reads what the request and url should carry for this key, default included. */
  readonly write: () => unknown;
  /**
   * Reads what the bar should draw as a pill, or nothing when the key sits at its default.
   *
   * Not the same question as {@link write}. A param source states the default because the backend
   * needs it, while a pill that says what would happen anyway is a control the user has to read and
   * dismiss for nothing: there, an absent pill *is* the default.
   */
  readonly pill: () => string | string[] | boolean | undefined;
}

function firstOf(raw: RawQueryValue): string | undefined {
  if (raw === undefined || raw === null || typeof raw === 'boolean')
    return undefined;
  return arrayify(raw)[0] ?? undefined;
}

/**
 * A single written or picked string, e.g. a location or a chain.
 *
 * @param model - the ref the key is stored in.
 * @param options - `admit` rejects a value the table cannot honour, which the url can carry and the
 * bar cannot produce.
 */
export function stringParam(
  model: Ref<string>,
  options: { admit?: (value: string) => boolean } = {},
): ParamRef {
  const { admit } = options;
  return {
    pill: (): string | undefined => get(model) === '' ? undefined : get(model),
    read: (raw: RawQueryValue): void => {
      const value = firstOf(raw) ?? '';
      set(model, admit === undefined || admit(value) ? value : '');
    },
    write: (): string => get(model),
  };
}

/**
 * A single picked value the table may simply not have, e.g. a chain no pill has named yet.
 *
 * Distinct from {@link stringParam} because the ref is the table's own: one holding `undefined`
 * cannot be handed an empty string without changing what the table reads as "nothing picked".
 *
 * @param model - the ref the key is stored in.
 * @param options - `admit` rejects a value the table cannot honour.
 */
export function optionalStringParam(
  model: Ref<string | undefined>,
  options: { admit?: (value: string) => boolean } = {},
): ParamRef {
  const { admit } = options;
  return {
    pill: (): string | undefined => get(model),
    read: (raw: RawQueryValue): void => {
      const value = firstOf(raw);
      const admitted = value !== undefined && (admit === undefined || admit(value));
      set(model, admitted ? value : undefined);
    },
    write: (): string | undefined => get(model),
  };
}

/**
 * A list of picked values.
 *
 * Always written as the array itself, never pre-joined. The url half of a source stringifies what
 * it is given, and an array stringifies to its comma-joined form, so a key reaches the request as a
 * list and the url as `a,b` without this having to choose between them. Joining here instead would
 * put the joined string in the request payload too.
 *
 * @param model - the ref the key is stored in.
 * @param options - `admit` filters out values the table cannot honour. `separator` says the url
 * carries this key as one joined string, which is the read side of the stringification above; a key
 * repeated in the query instead needs no separator.
 */
export function listParam(
  model: Ref<string[]>,
  options: { admit?: (value: string) => boolean; separator?: string } = {},
): ParamRef {
  const { admit, separator } = options;
  return {
    pill: (): string[] | undefined => get(model).length === 0 ? undefined : get(model),
    read: (raw: RawQueryValue): void => {
      if (raw === undefined || raw === null || typeof raw === 'boolean') {
        set(model, []);
        return;
      }
      const written = arrayify(raw).filter((entry): entry is string => typeof entry === 'string');
      const values = separator === undefined
        ? written
        : written.flatMap(entry => entry.split(separator)).filter(entry => entry.length > 0);
      set(model, admit === undefined ? values : values.filter(admit));
    },
    write: (): string[] => get(model),
  };
}

/**
 * A flag whose presence is its value. Absent, and anything other than `true`, reads as off: a
 * boolean param is written only by the thing that turns it on, so there is no third state to keep.
 *
 * @param model - the ref the key is stored in.
 */
export function boolParam(model: Ref<boolean>): ParamRef {
  return {
    // Off is the absence of the pill, which is the whole of a boolean field's state.
    pill: (): true | undefined => get(model) ? true : undefined,
    // `true` from the bar's bag, the written `'true'` from a url.
    read: (raw: RawQueryValue): void => {
      set(model, raw === true || firstOf(raw) === 'true');
    },
    write: (): boolean => get(model),
  };
}

/**
 * One of a known set, falling back when the url names something else.
 *
 * The fallback matters more than it looks. Several of these keys reach both the request and a
 * label, so an unrecognised one would be sent on while the UI claimed something different.
 *
 * @param model - the ref the key is stored in.
 * @param isValid - whether a raw value names a member of the set.
 * @param fallback - what an absent or unrecognised value reads as, which is the table's default.
 */
export function enumParam<T extends string>(
  model: Ref<T>,
  isValid: (value: string) => value is T,
  fallback: T,
): ParamRef {
  return {
    pill: (): T | undefined => get(model) === fallback ? undefined : get(model),
    read: (raw: RawQueryValue): void => {
      const value = firstOf(raw);
      set(model, value !== undefined && isValid(value) ? value : fallback);
    },
    write: (): T => get(model),
  };
}

/**
 * A `ParamSource` whose two directions are derived from one declaration per key, rather than
 * written twice as a `values` computed and a `fromQuery` that has to mirror it by hand.
 *
 * Deliberately knows nothing about the router, or about what a key means. It reads whichever query
 * it is handed, which is what lets a nested table use it: that table owns no route, and its query
 * is a ref the parent encodes into a param of its own. `to` and `skipEmpty` stay with the caller
 * for the same reason, since whether a key reaches the request, resets the page, or only rides the
 * url is a decision about the key rather than about how it is spelled.
 */
export function refParams(
  spec: Record<string, ParamRef>,
  options: Omit<ParamSource, 'values' | 'fromQuery'>,
): ParamSource {
  const entries = Object.entries(spec);

  return {
    ...options,
    fromQuery(query: LocationQuery): void {
      for (const [key, param] of entries)
        param.read(query[key]);
    },
    values: computed<Record<string, unknown>>(
      () => Object.fromEntries(entries.map(([key, param]) => [key, param.write()])),
    ),
  };
}

/**
 * The pill bar's `params` model over the same declarations a {@link refParams} source is built
 * from, so a param-bound pill and the request it reaches are one statement rather than two
 * adapters onto the same refs.
 *
 * A key at its default is left out: the bar decides a pill exists by the key being there, and
 * removing the pill is how a filter is turned off. That is the one place this differs from the
 * param source, which states the default because the backend needs it.
 *
 * A plain factory rather than a composable: it injects nothing and owns no lifecycle, so the
 * writable computed it returns is the caller's to bind.
 */
export function toPillParams(spec: Record<string, ParamRef>): WritableComputedRef<PillParams> {
  const entries = Object.entries(spec);

  return computed<PillParams>({
    get(): PillParams {
      const bag: PillParams = {};
      for (const [key, param] of entries) {
        const value = param.pill();
        if (value !== undefined)
          bag[key] = value;
      }
      return bag;
    },
    set(bag: PillParams): void {
      for (const [key, param] of entries)
        param.read(bag[key]);
    },
  });
}
