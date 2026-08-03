import type { ContextColorsType, RuiIcons } from '@rotki/ui-library';
import type { AssetsWithId } from '@/modules/assets/types';
import type { FilterOp, FilterValueType } from '@/modules/core/table/filtering';

export type { FilterOp, FilterValueType };

/**
 * How a filter value is drawn: which icon stands in front of it and, for an address, whether it
 * gets a face. Named constants rather than bare literals so a new kind is added in one place and
 * every consumer that must handle it fails to compile until it does.
 */
export const DisplayKinds = {
  /** A tracked account: avatar plus its name, with the address as the caption. */
  ACCOUNT: 'account',
  /** A bare address: the same avatar, but the address itself is the label. */
  ADDRESS: 'address',
  ASSET: 'asset',
  /** A blockchain: its chain logo, e.g. the account filter's chain values. */
  CHAIN: 'chain',
  COUNTERPARTY: 'counterparty',
  LOCATION: 'location',
} as const;

export type DisplayKind = typeof DisplayKinds[keyof typeof DisplayKinds];

/** A plain icon standing in for one filter value, resolved by the field that owns the value. */
export interface ValueIcon {
  readonly icon: RuiIcons;
  readonly color?: ContextColorsType;
}

/**
 * The colours one value is drawn in when the value *is* a colour, which today means a tag: a tag
 * carries its own pair and is recognised by it everywhere else in the app. CSS colours, not an
 * `RuiIcons`/`ContextColorsType` pair like `ValueIcon`, because the pair is the user's own choice.
 */
export interface ValueSwatch {
  readonly background: string;
  readonly foreground: string;
}

/**
 * Where a field's value is transported when the state is serialized.
 *
 * - `matcher`: flows through the `matches` object (`MatchedKeywordWithBehaviour`), exactly
 *   like the current `TableFilter` bar.
 * - `param`: flows through a `useServerTable` param source (request and/or url), which is
 *   how today's *external* filters (e.g. history account `locationLabels`) are transported.
 *   Modelling them as fields is what lets the pill bar absorb external filters into one bar.
 */
export type FieldBinding =
  | { readonly kind: 'matcher' }
  | { readonly kind: 'param'; readonly paramKey: string; readonly to: 'request' | 'url' | 'both' };

/**
 * A normalized, presentation-facing view of a `SearchMatcher` or an external param filter.
 * The one shape the pill components read, so they never branch on the matcher discriminant.
 */
export interface FieldDef {
  readonly key: string;
  readonly label: string;
  readonly valueType: FilterValueType;
  /** Allowed operators, most-default first (never empty). */
  readonly operators: readonly FilterOp[];
  readonly multiple: boolean;
  readonly binding: FieldBinding;
  readonly allowExclusion: boolean;
  /**
   * Keys of fields this one cannot coexist with, because they write the same wire keys. History's
   * `action` is one presentation of an event type/subtype pair, so offering it beside the Type and
   * Subtype fields would let two pills fight over the same request params. A field with an active
   * filter removes everything it excludes from the bar's add menu and narrowing, in both
   * directions — declare the pair on both sides.
   */
  readonly excludes?: readonly string[];
  /**
   * A string field with no option list: the user types the value(s) (e.g. notes substring, a tx
   * hash, an address). Rendered by the text editor instead of the checklist. Serializes as an
   * enum (its typed string values), so the wire form is unchanged.
   */
  readonly freeText?: boolean;
  readonly hint?: string;
  /**
   * How a value renders in the option list / pill: a `counterparty`/`location` icon, an
   * `asset` icon+symbol, or an `account` avatar+name, resolved from the value string. Absent =
   * plain text.
   */
  readonly display?: DisplayKind;
  /**
   * Maps a value to a plain icon shown before it, for a field whose values are neither an
   * identity nor a rich display kind but are still scanned by their icon (e.g. the history event
   * state markers, which are read by their glyph and colour). Resolution lives with the field, so
   * the shared icon component stays domain-free. Takes precedence over `display`.
   */
  readonly resolveIcon?: (value: string) => ValueIcon | undefined;
  /**
   * Maps a value to the colour pair it is drawn in, for a field whose values carry colours of the
   * user's own choosing (tags). Rendered as a small swatch before the value, the same colours the
   * tag chip uses elsewhere. Takes precedence over `display`, and `resolveIcon` takes precedence
   * over it.
   */
  readonly resolveSwatch?: (value: string) => ValueSwatch | undefined;
  /**
   * Whether a value's label is still being resolved, drawn as a skeleton row instead of the label.
   * An account is the case that needs it: its ENS name arrives after the list does, and showing
   * the address first meant every named row visibly flipped a moment later.
   */
  readonly resolveLoading?: (value: string) => boolean;
  /**
   * Reads a value stored by the old filter bar into the form this field now takes, for a field
   * that used to be matcher-bound and is now param-bound. Returning nothing drops the value.
   * Only the accounts table needs it, whose account filter stored `label (address)` where the
   * field now wants the address alone. Lives on the field because it is the only thing that knows
   * both forms; without it a converted saved filter would lose that pill silently.
   */
  readonly fromLegacy?: (value: string) => string | undefined;
  /**
   * Maps a raw wire value to the human label shown on the collapsed pill (e.g. an account
   * address to its ENS/tracked name). Absent = the raw value is shown. Domain-specific
   * resolution lives with the field so the pure format layer stays domain-free.
   */
  readonly resolveLabel?: (value: string) => string;
  /**
   * Muted secondary text shown after the value on a single-value pill (e.g. an account's address
   * under its name). Only rendered when exactly one value is active. Absent = no secondary text.
   */
  readonly resolveCaption?: (value: string) => string | undefined;
  /**
   * Extra text the bar's narrowing input matches a value on, beyond its display label. An account
   * is the case that needs it: its label is a name, or a truncated and scrambled address, so
   * neither a full address nor an ENS name would ever match what is shown. Returning
   * `address name tags` makes all three findable while the row still renders its label.
   */
  readonly resolveKeywords?: (value: string) => string | undefined;
  /**
   * Maps a value to the chain it belongs to (e.g. an asset identifier to `base`), rendered as a
   * chain icon after the value. An asset symbol is ambiguous across chains, and the asset icon's
   * own corner badge is too small to read at pill size, so the chain is shown as its own icon.
   */
  readonly resolveChain?: (value: string) => string | undefined;
  /**
   * For a collapsed `range`/`date` field, the two wire keys its bounds serialize to: a `range`'s
   * min/max or a `date`'s from/to are each folded from two separate backend matchers into one
   * pill (e.g. the events filter's `minAmount`/`maxAmount`, or period's `fromTimestamp`/
   * `toTimestamp`). `lower` carries `range.min` / `date.from`; `upper` carries `range.max` /
   * `date.to`. Matcher-bound only. The optional `serializer`/`deserializer` apply to each bound.
   */
  readonly bounds?: { readonly lower: string; readonly upper: string };
  /**
   * Formats a raw bound value for display on the pill (e.g. a `date` field's unix-second bound to
   * a human date). Display-only: the stored/wire value keeps its raw form. Range/date fields only.
   */
  readonly formatBound?: (value: string) => string;
  /** Synchronous enum suggestions (string matcher). */
  readonly suggest?: () => string[];
  /** Asynchronous asset search (asset matcher). */
  readonly searchAsset?: (value: string) => Promise<AssetsWithId>;
  /** Optional per-value validator (e.g. a well-formed tx hash / address); invalid input is rejected. */
  readonly validate?: (value: string) => boolean;
  /**
   * Reads what was typed into the bar's inline input as whole filters on this field, for the
   * fields whose values are written rather than picked: `>100` on an amount, `15/01/2024` on a
   * date. Returns one draft when the query says which direction it means and two when it does not
   * (a bare `100` is both "at least" and "at most"), or nothing when the query is not a value for
   * this field at all. Interpretation lives with the field, so the narrowing layer needs no notion
   * of what a date looks like.
   */
  readonly parseTyped?: (query: string) => TypedFilterDraft[];
  /**
   * Already-translated message shown when `validate` rejects what was typed. Says what the field
   * wants ("Enter a valid transaction hash"), which a generic "Invalid value" cannot. Absent =
   * the editor's generic message.
   */
  readonly invalidHint?: string;
  /** Value serializer for the wire form (string matcher). */
  readonly serializer?: (value: string) => string;
  /** Value deserializer from the wire form (string matcher). */
  readonly deserializer?: (value: string) => string;
}

/**
 * The bar's copy, grouped into one prop so adding a string does not grow the component's
 * prop list. All are already-translated strings: the pill components never call `useI18n`.
 */
export interface PillBarLabels {
  /** `+ Add filter` button. */
  readonly add: string;
  /** `Clear all` button. */
  readonly clear: string;
  /** Placeholder of the field menu's search input. */
  readonly search: string;
  /** Shown when no field matches the field menu's search. */
  readonly empty: string;
  /** Placeholder of the bar's inline narrowing input. */
  readonly narrow: string;
  /** Shown when nothing matches what was typed in the inline input. */
  readonly narrowEmpty: string;
  /** Accessible name for a pill's remove control, which is an icon with no text of its own. */
  readonly remove: string;
}

/** One active filter, agnostic of presentation. */
export interface ActiveFilter {
  readonly fieldKey: string;
  readonly op: FilterOp;
  /** enum/asset values (multi). */
  readonly values: string[];
  /** numeric range (valueType `range`). */
  readonly range?: { readonly min?: string; readonly max?: string };
  /** date range/preset (valueType `date`). */
  readonly date?: { readonly preset?: string; readonly from?: string; readonly to?: string };
}

export type FilterState = ActiveFilter[];

/**
 * A filter derived from what was typed into the bar, minus the field it belongs to. Declared here
 * rather than beside the parsers so `FieldDef` does not have to import from them.
 */
export type TypedFilterDraft = Omit<ActiveFilter, 'fieldKey'>;
