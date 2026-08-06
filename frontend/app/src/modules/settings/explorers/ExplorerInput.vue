<script setup lang="ts">
import type { ZodType } from 'zod';
import { useForm } from '@/modules/core/form/use-form';
import { EXPLORER_URL_FIELD, explorerUrlSchema, type ExplorerUrlState } from '@/modules/settings/explorers/explorer-url-schema';

defineOptions({
  inheritAttrs: false,
});

const url = defineModel<string>({ required: true });

const emit = defineEmits<{
  'save-data': [value?: string];
}>();

const { t } = useI18n({ useScope: 'global' });

const schema = computed<ZodType>(() => explorerUrlSchema({
  https: t('explorer_input.validation.https'),
  url: t('explorer_input.validation.url'),
}));

/** The parent owns the persist and listens for `save-data`, so submitting here is a no-op. */
const form = useForm<ExplorerUrlState, ExplorerUrlState>({
  initial: (): ExplorerUrlState => ({ url: get(url) }),
  schema,
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: (state): ExplorerUrlState => ({ url: state.url }),
});

/** The form api is a plain object, so its refs only unwrap in the template through a local one. */
const invalid = computed<boolean>(() => !get(form.valid));

function saveData(value?: string) {
  emit('save-data', value);
}

watch(() => form.state.url, (value) => {
  set(url, value);
});

// The settings page reseeds every field when the user switches chain.
watch(url, (value) => {
  if (value !== form.state.url)
    form.state.url = value;
});
</script>

<template>
  <div class="flex items-start gap-4">
    <RuiTextField
      v-model="form.state.url"
      class="flex-1"
      variant="outlined"
      color="primary"
      clearable
      :error-messages="form.errors(EXPLORER_URL_FIELD)"
      v-bind="$attrs"
      @update:model-value="form.touch(EXPLORER_URL_FIELD)"
      @clear="saveData()"
    />
    <RuiButton
      variant="text"
      class="mt-1"
      icon
      :disabled="invalid"
      @click="saveData(form.state.url)"
    >
      <RuiIcon name="lu-save" />
    </RuiButton>
  </div>
</template>
