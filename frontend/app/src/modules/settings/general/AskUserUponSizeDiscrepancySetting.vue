<script setup lang="ts">
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const { dialog = false, confirm = false } = defineProps<{
  dialog?: boolean;
  confirm?: boolean;
}>();

const value = ref<boolean>(false);
const { askUserUponSizeDiscrepancy } = storeToRefs(useGeneralSettingsStore());

watchImmediate(askUserUponSizeDiscrepancy, (askUser) => {
  set(value, !get(askUser));
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsOption setting="askUserUponSizeDiscrepancy">
    <template
      v-if="!dialog"
      #title
    >
      {{ t('sync_indicator.setting.ask_user_upon_size_discrepancy.title') }}
    </template>
    <template #default="{ error, success, updateImmediate }">
      <RuiCheckbox
        v-if="confirm"
        :model-value="value"
        :label="t('sync_indicator.setting.ask_user_upon_size_discrepancy.confirm_label')"
        color="primary"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateImmediate(!$event)"
      />
      <RuiSwitch
        v-else
        :model-value="value"
        :size="dialog ? 'sm' : undefined"
        :class="{
          '[&_span]:text-sm [&_span]:mt-0.5': dialog,
        }"
        :label="t('sync_indicator.setting.ask_user_upon_size_discrepancy.label')"
        color="primary"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateImmediate(!$event)"
      />
    </template>
  </SettingsOption>
</template>
