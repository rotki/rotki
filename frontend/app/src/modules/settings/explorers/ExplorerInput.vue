<script setup lang="ts">
import type { ZodType } from 'zod';
import { noSubmit, useForm } from '@/modules/core/form/use-form';
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
  submit: noSubmit,
  transform: (state): ExplorerUrlState => ({ url: state.url }),
});

/** The url as last saved or seeded, so the save action only shows up for an actual change. */
const saved = ref<string>(get(url));

/** The form api is a plain object, so its refs only unwrap in the template through a local one. */
const invalid = computed<boolean>(() => !get(form.valid));

const changed = computed<boolean>(() => form.state.url !== get(saved));

function saveData(value?: string): void {
  set(saved, value ?? '');
  emit('save-data', value);
}

watch(() => form.state.url, (value) => {
  set(url, value);
});

// The settings page reseeds every field when the user switches chain.
watch(url, (value) => {
  if (value !== form.state.url) {
    form.state.url = value;
    set(saved, value);
  }
});
</script>

<template>
  <RuiTextField
    v-model="form.state.url"
    color="primary"
    clearable
    :error-messages="form.errors(EXPLORER_URL_FIELD)"
    v-bind="$attrs"
    @update:model-value="form.touch(EXPLORER_URL_FIELD)"
    @clear="saveData()"
    @keydown.enter="changed && !invalid && saveData(form.state.url)"
  >
    <template #append>
      <RuiButton
        v-if="changed"
        variant="text"
        color="primary"
        size="sm"
        :disabled="invalid"
        :aria-label="t('common.actions.save')"
        data-testid="explorer-save"
        @click="saveData(form.state.url)"
      >
        {{ t('common.actions.save') }}
      </RuiButton>
    </template>
  </RuiTextField>
</template>
