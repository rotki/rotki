<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { Defaults } from '@/modules/core/common/defaults';
import { useValidation } from '@/modules/core/common/use-validation';
import { toMessages } from '@/modules/core/common/validation/validation';
import DateFormatHelp from '@/modules/settings/controls/DateFormatHelp.vue';
import SettingResetConfirmButton from '@/modules/settings/SettingResetConfirmButton.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

const { t } = useI18n({ useScope: 'global' });

const { error: writeError, flush, model, success: writeSuccess } = useSettingModel('dateDisplayFormat', { debounce: 1500 });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

const dateDisplayFormat = ref<string>(get(model));
const formatHelp = ref<boolean>(false);
const now = new Date();
const defaultDateDisplayFormat = Defaults.DEFAULT_DATE_DISPLAY_FORMAT;

function containsValidDirectives(v: string): boolean {
  return displayDateFormatter.containsValidDirectives(v);
}

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
const dateDisplayFormatExample = computed<string>(() => displayDateFormatter.format(now, get(dateDisplayFormat)));

function successMessage(dateFormat: string): string {
  return t('general_settings.validation.date_display_format.success', {
    dateFormat,
  });
}

function onInput(value: string): void {
  clearAll();
  callIfValid(value, (format: string) => {
    set(model, format);
  });
}

async function reset(): Promise<void> {
  set(dateDisplayFormat, defaultDateDisplayFormat);
  set(model, defaultDateDisplayFormat);
  await flush();
}

watch(model, (value) => {
  if (value !== get(dateDisplayFormat))
    set(dateDisplayFormat, value);
});

watch(writeSuccess, (saved) => {
  if (saved)
    setSuccess(successMessage(get(model)), true);
});

watch(writeError, (message) => {
  if (message)
    setError(`${t('general_settings.validation.date_display_format.error')}: ${message}`, true);
});
</script>

<template>
  <div class="mb-6">
    <DateFormatHelp v-model="formatHelp" />
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
        @update:model-value="onInput($event)"
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
        @confirm="reset()"
      />
    </div>
  </div>
</template>
