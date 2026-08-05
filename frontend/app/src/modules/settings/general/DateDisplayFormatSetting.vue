<script setup lang="ts">
import type { ZodType } from 'zod';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { Defaults } from '@/modules/core/common/defaults';
import { useForm } from '@/modules/core/form/use-form';
import DateFormatHelp from '@/modules/settings/controls/DateFormatHelp.vue';
import { SETTING_FIELD, type SettingFieldState } from '@/modules/settings/controls/setting-field-schemas';
import { dateFormatSchema } from '@/modules/settings/general/date-format-schema';
import SettingResetConfirmButton from '@/modules/settings/SettingResetConfirmButton.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

const { t } = useI18n({ useScope: 'global' });

const { error: writeError, flush, model, success: writeSuccess } = useSettingModel('dateDisplayFormat', { debounce: 1500 });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

const formatHelp = ref<boolean>(false);
const now = new Date();
const defaultDateDisplayFormat = Defaults.DEFAULT_DATE_DISPLAY_FORMAT;

const schema = computed<ZodType>(() => dateFormatSchema({
  empty: t('general_settings.date_display.validation.empty'),
  invalid: t('general_settings.date_display.validation.invalid'),
}));

/** Submitting is the persist: the core runs it only when the field parses, as `callIfValid` did. */
const form = useForm<SettingFieldState, SettingFieldState>({
  initial: (): SettingFieldState => ({ value: get(model) }),
  schema,
  submit: async (payload: SettingFieldState): Promise<{ success: boolean }> => {
    set(model, payload.value);
    return Promise.resolve({ success: true });
  },
  transform: (state): SettingFieldState => ({ value: state.value }),
});

const dateDisplayFormatExample = computed<string>(() => displayDateFormatter.format(now, form.state.value));

function successMessage(dateFormat: string): string {
  return t('general_settings.validation.date_display_format.success', {
    dateFormat,
  });
}

async function onInput(value: string): Promise<void> {
  clearAll();
  form.state.value = value;
  await form.submit();
}

async function reset(): Promise<void> {
  form.state.value = defaultDateDisplayFormat;
  set(model, defaultDateDisplayFormat);
  await flush();
}

// Reflect external changes into the field, but ignore the echo of our own writes (same string).
watch(model, (value) => {
  if (value !== form.state.value)
    form.state.value = value;
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
        v-model="form.state.value"
        variant="outlined"
        color="primary"
        data-cy="date-display-format-input"
        class="flex-grow"
        :label="t('general_settings.labels.date_display_format')"
        type="text"
        :success-messages="success"
        :error-messages="error || form.errors(SETTING_FIELD)"
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
