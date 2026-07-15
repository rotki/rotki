<script setup lang="ts">
import type { MessageKey } from '@/message-key';
import type { SettingKey } from '@/modules/settings/use-setting';
import { type ActionKey, anchorId, getActionEntry } from '@/modules/settings/settings-actions';
import { getRegistryEntry } from '@/modules/settings/settings-registry';

defineOptions({
  inheritAttrs: false,
});

const { actionKey, settingKey } = defineProps<{
  /**
   * When set, the item's DOM id and (fallback) title are single-sourced from that setting's registry
   * entry - its settings-search scroll target - instead of being restated here. A composite item wrapping
   * several settings under one anchor passes the representative key.
   */
  settingKey?: SettingKey;
  /**
   * The action counterpart to `settingKey` for a row backed by `settingsActions` rather than a registry
   * value (change password, purge data, ...). Resolves the same anchor/title through `anchorId`.
   */
  actionKey?: ActionKey;
}>();

defineSlots<{
  title?: () => unknown;
  subtitle?: () => unknown;
  default?: () => unknown;
}>();

const { t } = useI18n({ useScope: 'global' });

const anchor = computed<string | undefined>(() => {
  const key = settingKey ?? actionKey;
  return key ? anchorId(key) : undefined;
});

// The row's title, sourced from its registry search block or action entry so it is not restated in the
// template. A `#title` slot still overrides it (for rich content).
const registryTitle = computed<string | undefined>(() => {
  let titleKey: MessageKey | undefined;
  if (settingKey)
    titleKey = getRegistryEntry(settingKey)?.search?.titleKey;
  else if (actionKey)
    titleKey = getActionEntry(actionKey)?.titleKey;
  return titleKey ? t(titleKey) : undefined;
});
</script>

<template>
  <!-- :id (from the setting-key/action-key anchor) is bound before $attrs so an explicit :id still wins -->
  <div
    v-if="$slots.title || $slots.subtitle || registryTitle"
    :id="anchor"
    v-bind="$attrs"
    class="flex flex-col md:flex-row py-4 md:py-6 gap-4 md:gap-8 lg:gap-12 border-b border-default"
  >
    <div class="w-full md:w-[150px] lg:w-[200px] xl:w-[288px] shrink-0">
      <div
        v-if="$slots.title || registryTitle"
        class="font-medium"
      >
        <slot name="title">
          {{ registryTitle }}
        </slot>
      </div>
      <div
        v-if="$slots.subtitle"
        class="text-rui-text-secondary text-sm"
      >
        <slot name="subtitle" />
      </div>
    </div>
    <div class="flex-1 min-w-0">
      <slot />
    </div>
  </div>
  <slot v-else />
</template>
