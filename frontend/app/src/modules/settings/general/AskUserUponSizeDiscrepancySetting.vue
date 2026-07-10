<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { dialog = false, confirm = false } = defineProps<{
  dialog?: boolean;
  confirm?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsItem>
    <template
      v-if="!dialog"
      #title
    >
      {{ t('sync_indicator.setting.ask_user_upon_size_discrepancy.title') }}
    </template>
    <SettingSwitch
      setting="askUserUponSizeDiscrepancy"
      inverted
      :control="confirm ? 'checkbox' : 'switch'"
      :size="dialog ? 'sm' : undefined"
      :class="{
        '[&_span]:text-sm [&_span]:mt-0.5': dialog,
      }"
      :label="confirm
        ? t('sync_indicator.setting.ask_user_upon_size_discrepancy.confirm_label')
        : t('sync_indicator.setting.ask_user_upon_size_discrepancy.label')"
    />
  </SettingsItem>
</template>
