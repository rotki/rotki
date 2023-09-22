<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, requiredUnless } from '@vuelidate/validators';
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
  set(errorMessages, {});
};

async function merge() {
  set(pending, true);
  const result = await mergeAssets({
    sourceIdentifier: get(sourceIdentifier),
    targetIdentifier: get(targetIdentifier)
  });

  if (result.success) {
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
      requiredUnless(done)
    )
  },
  targetIdentifier: {
    required: helpers.withMessage(
      t('merge_dialog.target.non_empty').toString(),
      requiredUnless(done)
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
  <VDialog :value="value" max-width="500" persistent @input="input($event)">
    <Card>
      <template #title>{{ t('merge_dialog.title') }}</template>
      <template #subtitle>{{ t('merge_dialog.subtitle') }}</template>
      <template v-if="!done" #hint>{{ t('merge_dialog.hint') }}</template>
      <template #buttons>
        <VSpacer />
        <RuiButton variant="default" @click="input(false)">
          <span v-if="done">{{ t('common.actions.close') }}</span>
          <span v-else>
            {{ t('common.actions.cancel') }}
          </span>
        </RuiButton>
        <RuiButton
          v-if="!done"
          variant="default"
          color="primary"
          :disabled="v$.$invalid || pending"
          :loading="pending"
          @click="merge()"
        >
          {{ t('merge_dialog.merge') }}
        </RuiButton>
      </template>

      <div v-if="done">{{ t('merge_dialog.done') }}</div>

      <VForm v-else :value="!v$.$invalid">
        <!-- We use `v-text-field` here instead `asset-select` -->
        <!-- because the source can be filled with unknown identifier -->
        <VTextField
          v-model="sourceIdentifier"
          :label="t('merge_dialog.source.label')"
          :error-messages="toMessages(v$.sourceIdentifier)"
          outlined
          :disabled="pending"
          persistent-hint
          :hint="t('merge_dialog.source_hint')"
          @focus="clearErrors()"
          @blur="v$.sourceIdentifier.$touch()"
        />
        <VRow align="center" justify="center" class="my-4">
          <VCol cols="auto">
            <VIcon>mdi-arrow-down</VIcon>
          </VCol>
        </VRow>
        <AssetSelect
          v-model="targetIdentifier"
          outlined
          :error-messages="toMessages(v$.targetIdentifier)"
          :label="t('merge_dialog.target.label')"
          :disabled="pending"
          @focus="clearErrors()"
          @blur="v$.targetIdentifier.$touch()"
        />
      </VForm>
    </Card>
  </VDialog>
</template>
