<script setup lang="ts">
import type { ZodType } from 'zod';
import { numberSettingSchema } from '@/modules/settings/controls/setting-field-schemas';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { useMonitorService } from '@/modules/shell/app/use-monitor-service';

const {
  defaultValue,
  hint = '',
  label = '',
  min = 1,
  minValueMessage,
  requiredMessage,
  setting,
} = defineProps<{
  setting: 'queryRetryLimit' | 'connectTimeout' | 'readTimeout';
  min?: number;
  requiredMessage: string;
  minValueMessage: (min: number) => string;
  label?: string;
  hint?: string;
  defaultValue: number;
}>();

const { restart } = useMonitorService();

const schema = computed<ZodType>(() => numberSettingSchema({
  messages: { min: minValueMessage(min), required: requiredMessage },
  min,
}));
</script>

<template>
  <SettingsItem :setting-key="setting">
    <template #title>
      {{ label }}
    </template>
    <template #subtitle>
      {{ hint }}
    </template>
    <SettingNumber
      class="mt-1"
      :setting="setting"
      :schema="schema"
      :default="defaultValue"
      @updated="restart()"
    />
  </SettingsItem>
</template>
