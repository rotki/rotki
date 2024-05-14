<script setup lang="ts">
withDefaults(
  defineProps<{
    dialog?: boolean;
    confirm?: boolean;
  }>(),
  { dialog: false, confirm: false },
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
  >
    <RuiCheckbox
      v-if="confirm"
      :value="value"
      :label="t('sync_indicator.setting.ask_user_upon_size_discrepancy.confirm_label')"
      color="primary"
      :success-messages="success"
      :error-messages="error"
      @input="updateImmediate(!$event)"
    />
    <RuiSwitch
      v-else
      :value="value"
      :size="dialog ? 'sm' : undefined"
      :class="{ '[&_span]:text-sm [&_span]:mt-0.5': dialog }"
      :label="t('sync_indicator.setting.ask_user_upon_size_discrepancy.label')"
      color="primary"
      :success-messages="success"
      :error-messages="error"
      @input="updateImmediate(!$event)"
    />
  </SettingsOption>
</template>
