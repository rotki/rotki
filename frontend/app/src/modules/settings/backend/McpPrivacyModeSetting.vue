<script setup lang="ts">
import { RuiAlert, RuiChip, RuiRadio, RuiRadioGroup } from '@rotki/ui-library';
import { useTimeoutFn } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { McpPrivacyMode, type McpPrivacyMode as McpPrivacyModeValue } from '@/modules/settings/types/mcp';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import McpPrivacyPreview from './McpPrivacyPreview.vue';

const { t } = useI18n({ useScope: 'global' });

const {
  error: privacyModeError,
  model: privacyMode,
  pending: privacyModePending,
  success: privacyModeSuccess,
} = useSettingModel('mcpPrivacyMode');

/**
 * Whether the saved confirmation is still news.
 *
 * @remarks
 * `useSettingModel` holds `success` true until the next write, which beside a heading would read as
 * a permanent label rather than a confirmation, so it is shown on its own timer instead.
 */
const savedVisible = ref<boolean>(false);
const { start: hideSaved } = useTimeoutFn(() => {
  set(savedVisible, false);
}, 4000, { immediate: false });

interface PrivacyModeOption {
  readonly classes: string;
  readonly description: string;
  /** The backend default, and the one the copy points at. */
  readonly recommended: boolean;
  readonly title: string;
  readonly value: McpPrivacyModeValue;
}

/**
 * Picks the border and fill one privacy-mode option is drawn with.
 *
 * @remarks
 * Raw is tinted with the warning colour instead of the ordinary selected tint, because it is the
 * only mode that sends anything unmasked and picking it should not look like a routine choice.
 *
 * @param value - the option being drawn.
 * @param selected - the mode in effect; anything else gets the plain unselected border.
 */
function optionClasses(value: McpPrivacyModeValue, selected: McpPrivacyModeValue): string {
  if (value !== selected)
    return 'border-default';

  return value === McpPrivacyMode.RAW
    ? 'border-rui-warning/50 bg-rui-warning/10'
    : 'border-rui-primary bg-rui-primary/5';
}

const privacyModes = computed<PrivacyModeOption[]>(() => {
  const selected = get(privacyMode);
  return [
    {
      classes: optionClasses(McpPrivacyMode.STRICT, selected),
      description: t('backend_settings.settings.mcp_server.privacy_mode.strict.description'),
      recommended: false,
      title: t('backend_settings.settings.mcp_server.privacy_mode.strict.title'),
      value: McpPrivacyMode.STRICT,
    },
    {
      classes: optionClasses(McpPrivacyMode.BALANCED, selected),
      description: t('backend_settings.settings.mcp_server.privacy_mode.balanced.description'),
      recommended: true,
      title: t('backend_settings.settings.mcp_server.privacy_mode.balanced.title'),
      value: McpPrivacyMode.BALANCED,
    },
    {
      classes: optionClasses(McpPrivacyMode.RAW, selected),
      description: t('backend_settings.settings.mcp_server.privacy_mode.raw.description'),
      recommended: false,
      title: t('backend_settings.settings.mcp_server.privacy_mode.raw.title'),
      value: McpPrivacyMode.RAW,
    },
  ];
});

watch(privacyModeSuccess, (saved) => {
  set(savedVisible, saved);
  if (saved)
    hideSaved();
});
</script>

<template>
  <section class="flex max-w-4xl flex-col gap-4">
    <div>
      <div class="flex flex-wrap items-baseline justify-between gap-x-4">
        <h6 class="text-h6 font-semibold">
          {{ t('backend_settings.settings.mcp_server.privacy_mode.label') }}
        </h6>
        <span
          v-if="savedVisible"
          class="text-sm text-rui-success"
        >
          {{ t('backend_settings.settings.mcp_server.privacy_mode.success') }}
        </span>
      </div>
      <p class="text-sm text-rui-text-secondary">
        {{ t('backend_settings.settings.mcp_server.privacy_mode.hint') }}
      </p>
    </div>

    <RuiAlert
      v-if="privacyModeError"
      type="error"
    >
      {{ t('backend_settings.settings.mcp_server.privacy_mode.error', { message: privacyModeError }) }}
    </RuiAlert>

    <RuiRadioGroup
      v-model="privacyMode"
      data-testid="mcp-privacy-mode"
      color="primary"
      details="hidden"
      :disabled="privacyModePending"
    >
      <RuiRadio
        v-for="option in privacyModes"
        :key="option.value"
        :value="option.value"
        class="mb-2 w-full rounded-sm border pl-4 transition-colors last:mb-0"
        :class="option.classes"
      >
        <div class="py-2 pr-3">
          <div class="flex items-center gap-2 font-medium">
            {{ option.title }}
            <RuiChip
              v-if="option.recommended"
              size="sm"
              color="success"
            >
              {{ t('backend_settings.settings.mcp_server.privacy_mode.default') }}
            </RuiChip>
          </div>
          <div class="mt-0.5 max-w-prose text-sm text-rui-text-secondary">
            {{ option.description }}
          </div>
        </div>
      </RuiRadio>
    </RuiRadioGroup>

    <RuiAlert
      v-if="privacyMode === McpPrivacyMode.RAW"
      type="warning"
    >
      <strong>
        {{ t('backend_settings.settings.mcp_server.privacy_mode.raw_warning.title') }}
      </strong>
      {{ t('backend_settings.settings.mcp_server.privacy_mode.raw_warning.description') }}
    </RuiAlert>

    <McpPrivacyPreview :mode="privacyMode" />
  </section>
</template>
