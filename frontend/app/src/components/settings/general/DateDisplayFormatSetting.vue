<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import DateFormatHelp from '@/components/settings/controls/DateFormatHelp.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { displayDateFormatter } from '@/modules/common/date-formatter';
import { Defaults } from '@/modules/common/defaults';
import { toMessages } from '@/modules/common/validation/validation';
import SettingResetConfirmButton from '@/modules/settings/SettingResetConfirmButton.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const dateDisplayFormat = ref<string>('');
const formatHelp = ref<boolean>(false);
const now = new Date();
const defaultDateDisplayFormat = Defaults.DEFAULT_DATE_DISPLAY_FORMAT;

function containsValidDirectives(v: string) {
  return displayDateFormatter.containsValidDirectives(v);
}

const { t } = useI18n({ useScope: 'global' });

const rules = {
  dateDisplayFormat: {
    containsValidDirectives: helpers.withMessage(
      t('general_settings.date_display.validation.invalid'),
      containsValidDirectives,
    ),
    required: helpers.withMessage(t('general_settings.date_display.validation.empty'), required),
  },
};

const v$ = useVuelidate(rules, { dateDisplayFormat }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);
const { dateDisplayFormat: format } = storeToRefs(useGeneralSettingsStore());
const dateDisplayFormatExample = computed<string>(() => displayDateFormatter.format(now, get(dateDisplayFormat)));

function resetDateDisplayFormat() {
  set(dateDisplayFormat, get(format));
}

function successMessage(dateFormat: string) {
  return t('general_settings.validation.date_display_format.success', {
    dateFormat,
  });
}

onMounted(() => {
  resetDateDisplayFormat();
});
</script>

<template>
  <div class="mb-6">
    <DateFormatHelp v-model="formatHelp" />
    <SettingsOption
      #default="{ error, success, update, updateImmediate }"
      setting="dateDisplayFormat"
      :error-message="t('general_settings.validation.date_display_format.error')"
      :success-message="successMessage"
      @finished="resetDateDisplayFormat()"
    >
      <div class="flex items-start w-full">
        <RuiTextField
          v-model="dateDisplayFormat"
          variant="outlined"
          color="primary"
          data-cy="date-display-format-input"
          class="flex-grow"
          :label="t('general_settings.labels.date_display_format')"
          type="text"
          :success-messages="success"
          :error-messages="error || toMessages(v$.dateDisplayFormat)"
          :hint="
            t('general_settings.date_display_format_hint', {
              format: dateDisplayFormatExample,
            })
          "
          @update:model-value="callIfValid($event, update)"
        >
          <template #append>
            <RuiButton
              size="sm"
              variant="text"
              icon
              @click="formatHelp = true"
            >
              <RuiIcon name="lu-info" />
            </RuiButton>
          </template>
        </RuiTextField>
        <SettingResetConfirmButton
          :tooltip="t('general_settings.date_display_tooltip')"
          @confirm="updateImmediate(defaultDateDisplayFormat)"
        />
      </div>
    </SettingsOption>
  </div>
</template>
