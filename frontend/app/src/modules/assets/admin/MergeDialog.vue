<script setup lang="ts">
import type { AssetInfoWithId } from '@rotki/common';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { z, type ZodType } from 'zod';
import { useAssets } from '@/modules/assets/use-assets';
import { requiredField } from '@/modules/core/form/fields';
import { toServerErrors } from '@/modules/core/form/server-errors';
import { useForm } from '@/modules/core/form/use-form';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';

interface MergePayload {
  sourceIdentifier: string;
  targetIdentifier: string;
}

const display = defineModel<boolean>({ required: true });

const { sourceIdentifier: propSourceIdentifier, targetIdentifier: propTargetIdentifier } = defineProps<{
  sourceIdentifier?: string;
  targetIdentifier?: string;
}>();

const emit = defineEmits<{
  merged: [events: MergePayload];
}>();

const { t } = useI18n({ useScope: 'global' });

const { mergeAssets } = useAssets();

const done = ref<boolean>(false);
const target = ref<AssetInfoWithId>();

const schema = computed<ZodType>(() => z.object({
  sourceIdentifier: requiredField(t('merge_dialog.source.non_empty')),
  targetIdentifier: requiredField(t('merge_dialog.target.non_empty')),
}));

const form = useForm<MergePayload, MergePayload, string | ValidationErrors>({
  initial: (): MergePayload => ({ sourceIdentifier: '', targetIdentifier: '' }),
  schema,
  submit: async (payload: MergePayload) => mergeAssets(payload),
  transform: (state): MergePayload => ({
    sourceIdentifier: state.sourceIdentifier,
    targetIdentifier: state.targetIdentifier,
  }),
});

// Destructured, because a ref reached through `form.` in the template is not unwrapped and
// would read as permanently truthy.
const { errorCount, submitting, valid } = form;

// The button is also blocked while a server error stands, which vuelidate did through
// $externalResults feeding $invalid. The core keeps the two apart, so the count is read here.
const blocked = computed<boolean>(() => !get(valid) || get(errorCount) > 0 || get(submitting));

const excluded = computed<string[]>(() => {
  const source = form.state.sourceIdentifier;
  return source ? [source] : [];
});

function reset(): void {
  set(done, false);
  form.reset();
  set(target, undefined);
}

function clearErrors(): void {
  set(done, false);
  form.setServerErrors({});
}

async function merge(): Promise<void> {
  const result = await form.submit();

  if (result.outcome === 'success') {
    emit('merged', result.payload);
    reset();
    set(done, true);
  }
  else if (result.outcome === 'error') {
    const { message } = result;
    form.setServerErrors(typeof message === 'object'
      ? toServerErrors(message)
      : { sourceIdentifier: [message || t('merge_dialog.error')] });
  }
}

function input(value: boolean): void {
  set(display, value);
  setTimeout(reset, 100);
}

watch([display, () => propSourceIdentifier, () => propTargetIdentifier], ([isDisplayed, propSource, propTarget]) => {
  if (isDisplayed) {
    if (propSource) {
      form.state.sourceIdentifier = propSource;
    }
    if (propTarget) {
      form.state.targetIdentifier = propTarget;
    }
  }
});

watch(display, (isDisplayed) => {
  if (!isDisplayed) {
    reset();
  }
});
</script>

<template>
  <RuiDialog
    v-model="display"
    max-width="500"
  >
    <form
      novalidate
      @submit.stop.prevent="merge()"
    >
      <RuiCard>
        <template #header>
          {{ t('merge_dialog.title') }}
        </template>
        <template #subheader>
          {{ t('merge_dialog.subtitle') }}
        </template>
        <div class="mb-4 text-body-2 text-rui-text-secondary">
          {{ t('merge_dialog.hint') }}
        </div>

        <!-- We use `RuiTextField` here instead `asset-select` -->
        <!-- because the source can be filled with unknown identifier -->
        <RuiTextField
          v-model="form.state.sourceIdentifier"
          :label="t('merge_dialog.source.label')"
          :error-messages="form.errors('sourceIdentifier')"
          variant="outlined"
          color="primary"
          :disabled="submitting"
          :hint="t('merge_dialog.source_hint')"
          data-testid="merge-source"
          @focus="clearErrors()"
          @update:model-value="form.touch('sourceIdentifier')"
        />
        <div class="my-4 flex justify-center">
          <RuiIcon name="lu-arrow-down" />
        </div>
        <AssetSelect
          v-model="form.state.targetIdentifier"
          v-model:asset="target"
          variant="outlined"
          :error-messages="form.errors('targetIdentifier')"
          :label="t('merge_dialog.target.label')"
          :disabled="submitting"
          :source="{ excludes: excluded }"
          :hint="target ? t('merge_dialog.target_hint', { identifier: target.identifier }) : ''"
          data-testid="merge-target"
          @focus="clearErrors()"
          @update:model-value="form.touch('targetIdentifier')"
        />

        <RuiAlert
          v-if="done"
          class="mt-4"
          type="success"
        >
          {{ t('merge_dialog.done') }}
        </RuiAlert>
        <template #footer>
          <div class="grow" />
          <RuiButton
            variant="text"
            color="primary"
            @click="input(false)"
          >
            {{ t('common.actions.close') }}
          </RuiButton>
          <RuiButton
            color="primary"
            :disabled="blocked"
            :loading="submitting"
            type="submit"
            data-testid="merge-submit"
          >
            {{ t('merge_dialog.merge') }}
          </RuiButton>
        </template>
      </RuiCard>
    </form>
  </RuiDialog>
</template>
