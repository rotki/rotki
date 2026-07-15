import { msg } from '@/message-key';
import { useAnimationsEnabled } from '@/modules/session/use-animations-enabled';
import { SettingsCategoryIds, SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import { type RegistryEntry, session } from '@/modules/settings/settings-channels';

/** The `session` channel's registry slice: settings that live for the duration of the session only. */
export const sessionRegistry = {
  animationsEnabled: session('animationsEnabled', {
    anchor: SettingsHighlightIds.ANIMATIONS,
    mirror: useAnimationsEnabled,
    search: { category: SettingsCategoryIds.INTERFACE_ONLY, titleKey: msg.$t('frontend_settings.animations.title') },
  }),
  timeframe: session('timeframe'),
} satisfies Record<string, RegistryEntry>;
