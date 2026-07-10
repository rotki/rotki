<script setup lang="ts">
import { helpers, minValue, required } from '@vuelidate/validators';
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

const rules = {
  value: {
    min: helpers.withMessage(minValueMessage(min), minValue(min)),
    required: helpers.withMessage(requiredMessage, required),
  },
};
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ label }}
    </template>
    <template #subtitle>
      {{ hint }}
    </template>
    <SettingNumber
      class="mt-1"
      :setting="setting"
      :rules="rules"
      :default="defaultValue"
      @updated="restart()"
    />
  </SettingsItem>
</template>
