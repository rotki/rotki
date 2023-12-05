<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';

type Errors = Partial<
  Record<'targetIdentifier' | 'sourceIdentifier', string[]>
>;

defineProps<{ value: boolean }>();

const emit = defineEmits<{ (e: 'input', value: boolean): void }>();
const done = ref(false);
const errorMessages = ref<Errors>({});
const targetIdentifier = ref('');
const sourceIdentifier = ref('');
const pending = ref(false);

const { mergeAssets } = useAssets();
const { t } = useI18n();

const reset = () => {
  set(done, false);
  set(targetIdentifier, '');
  set(sourceIdentifier, '');
  set(pending, false);
  set(errorMessages, {});
  get(v$).$reset();
};

const clearErrors = () => {
  set(done, false);
  set(errorMessages, {});
};

async function merge() {
  set(pending, true);
  const result = await mergeAssets({
    sourceIdentifier: get(sourceIdentifier),
    targetIdentifier: get(targetIdentifier)
  });

  if (result.success) {
    reset();
    set(done, true);
  } else {
    set(
      errorMessages,
      typeof result.message === 'string'
        ? ({
            sourceIdentifier: [result.message || t('merge_dialog.error')]
          } satisfies Errors)
        : result.message
    );
    await get(v$).$validate();
  }
  set(pending, false);
}

const input = (value: boolean) => {
  emit('input', value);
  setTimeout(() => reset(), 100);
};

const rules = {
  sourceIdentifier: {
    required: helpers.withMessage(
      t('merge_dialog.source.non_empty').toString(),
      required
    )
  },
  targetIdentifier: {
    required: helpers.withMessage(
      t('merge_dialog.target.non_empty').toString(),
      required
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    sourceIdentifier,
    targetIdentifier
  },
  {
    $autoDirty: true,
    $externalResults: errorMessages
  }
);
</script>

<template>
  <VDialog :value="value" max-width="500" @input="input($event)">
    <RuiCard>
      <template #header>{{ t('merge_dialog.title') }}</template>
      <template #subheader>{{ t('merge_dialog.subtitle') }}</template>
      <div class="mb-4 text-body-2 text-rui-text-secondary">
        {{ t('merge_dialog.hint') }}
      </div>

      <form>
        <!-- We use `v-text-field` here instead `asset-select` -->
        <!-- because the source can be filled with unknown identifier -->
        <RuiTextField
          v-model="sourceIdentifier"
          :label="t('merge_dialog.source.label')"
          :error-messages="toMessages(v$.sourceIdentifier)"
          variant="outlined"
          color="primary"
          :disabled="pending"
          persistent-hint
          :hint="t('merge_dialog.source_hint')"
          @focus="clearErrors()"
          @blur="v$.sourceIdentifier.$touch()"
        />
        <div class="my-4 flex justify-center">
          <RuiIcon name="arrow-down-line" />
        </div>
        <AssetSelect
          v-model="targetIdentifier"
          outlined
          :error-messages="toMessages(v$.targetIdentifier)"
          :label="t('merge_dialog.target.label')"
          :disabled="pending"
          @focus="clearErrors()"
          @blur="v$.targetIdentifier.$touch()"
        />
      </form>

      <RuiAlert v-if="done" type="success">
        {{ t('merge_dialog.done') }}
      </RuiAlert>
      <template #footer>
        <div class="grow" />
        <RuiButton variant="text" color="primary" @click="input(false)">
          {{ t('common.actions.close') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :disabled="v$.$invalid || pending"
          :loading="pending"
          @click="merge()"
        >
          {{ t('merge_dialog.merge') }}
        </RuiButton>
      </template>
    </RuiCard>
  </VDialog>
</template>
