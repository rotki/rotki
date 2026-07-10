<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';
import CardTitle from '@/modules/shell/components/CardTitle.vue';

const emit = defineEmits<{
  updated: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div>
    <CardTitle>
      {{ t('statistics_graph_settings.infer_zero_timed_balances.title') }}
    </CardTitle>
    <SettingSwitch
      setting="inferZeroTimedBalances"
      size="sm"
      class="mt-4 [&_span]:!text-sm"
      :debounce="1500"
      :label="t('statistics_graph_settings.infer_zero_timed_balances.label')"
      @updated="emit('updated')"
    />
  </div>
</template>
