<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, url as urlValidator } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';

defineOptions({
  inheritAttrs: false,
});

const props = defineProps<{
  modelValue: string;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: string): void;
  (e: 'save-data', value?: string): void;
}>();

const { t } = useI18n();

const url = useSimpleVModel(props, emit);

function saveData(value?: string) {
  emit('save-data', value);
}

const isHttps = (value: string) => !value || value.startsWith('https');

const rules = {
  url: {
    urlValidator,
    https: helpers.withMessage(
      t('explorer_input.validation.https'),
      isHttps,
    ),
  },
};

const v$ = useVuelidate(
  rules,
  {
    url,
  },
  { $autoDirty: true },
);
</script>

<template>
  <div class="flex items-start gap-4">
    <RuiTextField
      v-model="url"
      class="flex-1"
      variant="outlined"
      color="primary"
      clearable
      :error-messages="toMessages(v$.url)"
      v-bind="$attrs"
      @click:clear="saveData()"
    />
    <RuiButton
      variant="text"
      class="mt-1"
      icon
      :disabled="v$.$invalid"
      @click="saveData(modelValue)"
    >
      <RuiIcon name="save-line" />
    </RuiButton>
  </div>
</template>
