<script setup lang="ts">
import { useGeneralSettingsStore } from '@/store/settings/general';

withDefaults(
  defineProps<{
    dialog?: boolean;
    confirm?: boolean;
  }>(),
  { confirm: false, dialog: false },
);

const value = ref(false);
const { askUserUponSizeDiscrepancy } = storeToRefs(useGeneralSettingsStore());

watchImmediate(askUserUponSizeDiscrepancy, (askUser) => {
  set(value, !get(askUser));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="askUserUponSizeDiscrepancy"
    :class="{
      '!py-0 border-b-0': dialog,
    }"
  >
    <div
      v-if="!dialog"
      class="py-2 pt-2"
    >
      <span class="font-medium">
        {{ t('sync_indicator.setting.ask_user_upon_size_discrepancy.title') }}
      </span>
    </div>
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
  </SettingsOption>
</template>
