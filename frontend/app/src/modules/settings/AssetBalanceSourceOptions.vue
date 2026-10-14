<script setup lang="ts">
import SettingsMenuSection from '@/modules/settings/SettingsMenuSection.vue';

/** The balance source choice for the asset graph, drawn inside whichever menu offers it. */
const useHistoricalBalances = defineModel<boolean>('source', { required: true });

const rememberForAsset = defineModel<boolean>('remember', { required: true });

defineProps<{
  asset?: string;
  name: string;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsMenuSection
    :title="t('statistics_graph_settings.source.title')"
    class="[&_label]:text-sm"
  >
    <RuiRadioGroup
      v-model="useHistoricalBalances"
      color="primary"
      size="sm"
      hide-details
    >
      <RuiRadio
        :label="t('statistics_graph_settings.source.snapshot')"
        :value="false"
      />
      <!-- eslint-disable vue/prefer-true-attribute-shorthand -- `value` is the radio payload, not a boolean prop, so the shorthand would pass an empty string -->
      <RuiRadio
        :label="t('statistics_graph_settings.source.historical_events_processing')"
        :value="true"
      />
      <!-- eslint-enable vue/prefer-true-attribute-shorthand -->
    </RuiRadioGroup>
    <p
      v-if="useHistoricalBalances"
      class="text-xs text-rui-text-secondary"
    >
      {{ t('statistics_graph_settings.source.warning') }}
    </p>
    <RuiCheckbox
      v-if="asset"
      v-model="rememberForAsset"
      hide-details
      size="sm"
      color="primary"
      :label="t('statistics_graph_settings.source.remember_state_for_asset', { asset: name })"
    />
  </SettingsMenuSection>
</template>
