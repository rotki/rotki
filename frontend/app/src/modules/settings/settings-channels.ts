import type { Ref } from 'vue';
import type { MessageKey } from '@/message-key';
import type { SessionSettings } from '@/modules/session/types';
import type { SettingsCategoryId, SettingsHighlightId } from '@/modules/settings/setting-highlight-ids';
import type { FrontendSettings } from '@/modules/settings/types/frontend-settings';
import type { AccountingSettings, GeneralSettings } from '@/modules/settings/types/user-settings';
import type { RouteName } from '@/types/router';

/**
 * A setting's opt-in to the settings search. Declaring `search` beside `anchor` makes one registry
 * entry the single source for the setting's value, its search row and (via the anchor) its scroll
 * target. Keys are i18n keys branded with `msg.$t` so the unused-key lint rules count them as used.
 * For a composite anchor (several keys, one highlight) only the representative key carries `search`,
 * so the anchor surfaces in exactly one search row.
 */
interface SettingSearch {
  /** The setting's own label, shown as the last breadcrumb segment of the search row. */
  readonly titleKey: MessageKey;
  /** The category header this row nests under (must be declared in `SEARCH_CATEGORIES`). */
  readonly category?: SettingsCategoryId;
  /** The tab a categoryless row sits directly on; used instead of `category` for a flat, headerless tab. */
  readonly tab?: RouteName;
  /** An intermediate breadcrumb segment for a sub-group within the category (e.g. a settings panel). */
  readonly group?: MessageKey;
  /** Extra i18n terms the search matches (subtitles, hints). */
  readonly keywords?: readonly MessageKey[];
}

/** Channel tag object: the single definition of the four settings channels. */
export const Channel = {
  accounting: 'accounting',
  frontend: 'frontend',
  general: 'general',
  session: 'session',
} as const;

export type SettingChannel = (typeof Channel)[keyof typeof Channel];

/** The parsed channel object type behind each channel tag. */
export interface ChannelTypeMap {
  accounting: AccountingSettings;
  frontend: FrontendSettings;
  general: GeneralSettings;
  session: SessionSettings;
}

/**
 * The loose runtime view of a registry entry, used by the runtime helpers (`getRegistryEntry`, the
 * repo effect runner, the write dispatcher). The entries themselves are the precise `FieldDef` /
 * `ProjectedDef` the channel builders produce; this is what they all satisfy.
 */
export interface RegistryEntry {
  readonly channel: SettingChannel;
  readonly wireKey?: string;
  readonly encode?: (value: any) => unknown;
  readonly project?: (settings: any) => unknown;
  readonly userFacing?: boolean;
  readonly effects?: ReadonlyArray<(settings: any) => void>;
  readonly mirror?: () => Ref<any>;
  /** The settings-search anchor (`SettingsHighlightId`) this key scrolls to; many keys may share one. */
  readonly anchor?: SettingsHighlightId;
  /** The settings-search row this key contributes, when it opts into registry-derived search. */
  readonly search?: SettingSearch;
}

/** A setting backed by a real field on its channel object, identified by the typed wire key `W`. */
/** @public referenced only through inferred types; the export is required for declaration emit. */
export interface FieldDef<C extends SettingChannel, W extends string> {
  readonly channel: C;
  readonly wireKey: W;
  readonly encode?: (value: any) => unknown;
  readonly userFacing?: boolean;
  readonly effects?: ReadonlyArray<(settings: any) => void>;
  readonly mirror?: () => Ref<any>;
  readonly anchor?: SettingsHighlightId;
  readonly search?: SettingSearch;
}

/** A read-only setting whose value is derived from the whole channel object (e.g. `currencySymbol`). */
/** @public referenced only through inferred types; the export is required for declaration emit. */
export interface ProjectedDef<C extends SettingChannel, V> {
  readonly channel: C;
  readonly project: (settings: any) => V;
  readonly userFacing?: boolean;
  readonly anchor?: SettingsHighlightId;
  readonly search?: SettingSearch;
}

interface FieldOptions<T, W extends keyof T> {
  /** Transforms the read value to its wire type on write, when they differ (e.g. Currency -> ticker). */
  readonly encode?: (value: T[W]) => unknown;
  /** `false` = internal state, excluded from settings forms and search. */
  readonly userFacing?: boolean;
  /** Post-persist side effects run against the whole channel object after this key changes. */
  readonly effects?: ReadonlyArray<(settings: T) => void>;
  /** External shared ref kept in sync with this key's value after each write. */
  readonly mirror?: () => Ref<T[W]>;
  /** Settings-search anchor this key scrolls to (a `SettingsHighlightId`); composites share one. */
  readonly anchor?: SettingsHighlightId;
  /** The settings-search row this key contributes, when it opts into registry-derived search. */
  readonly search?: SettingSearch;
}

interface ProjectedOptions {
  readonly userFacing?: boolean;
  readonly anchor?: SettingsHighlightId;
  readonly search?: SettingSearch;
}

/**
 * Per-channel entry builder. `channel('wireKey', opts)` declares a field-backed setting: the wire key
 * is constrained to `keyof ChannelSettings`, so a typo or a stale field name fails to compile, and
 * `encode`/`mirror`/`effects` are typed against that field's value. `channel.projected(fn)` declares a
 * read-only derived setting.
 */
interface ChannelBuilder<C extends SettingChannel> {
  <W extends keyof ChannelTypeMap[C] & string>(
    wireKey: W,
    options?: FieldOptions<ChannelTypeMap[C], W>,
  ): FieldDef<C, W>;
  readonly projected: <V>(
    project: (settings: ChannelTypeMap[C]) => V,
    options?: ProjectedOptions,
  ) => ProjectedDef<C, V>;
}

function defineChannel<C extends SettingChannel>(channel: C): ChannelBuilder<C> {
  type T = ChannelTypeMap[C];
  const field = <W extends keyof T & string>(wireKey: W, options: FieldOptions<T, W> = {}): FieldDef<C, W> => ({
    channel,
    wireKey,
    ...options,
  });
  const projected = <V>(project: (settings: T) => V, options: ProjectedOptions = {}): ProjectedDef<C, V> => ({
    channel,
    project,
    ...options,
  });
  return Object.assign(field, { projected });
}

export const general = defineChannel(Channel.general);

export const frontend = defineChannel(Channel.frontend);

export const session = defineChannel(Channel.session);

export const accounting = defineChannel(Channel.accounting);
