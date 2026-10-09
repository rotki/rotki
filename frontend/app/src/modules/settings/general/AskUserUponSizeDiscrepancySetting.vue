<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { dialog = false, confirm = false } = defineProps<{
  dialog?: boolean;
  confirm?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const [DefineSwitch, ReuseSwitch] = createReusableTemplate();
</script>

<template>
  <DefineSwitch>
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
  </DefineSwitch>

  <!-- in a menu or dialog only the switch: SettingsItem draws the settings page's titled row, which a narrow popup squeezes -->
  <ReuseSwitch v-if="dialog" />
  <SettingsItem
    v-else
    setting-key="askUserUponSizeDiscrepancy"
  >
    <template #title>
      {{ t('sync_indicator.setting.ask_user_upon_size_discrepancy.title') }}
    </template>
    <ReuseSwitch />
  </SettingsItem>
</template>
