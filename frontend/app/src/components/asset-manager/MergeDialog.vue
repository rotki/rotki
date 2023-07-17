<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, requiredUnless } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';

defineProps<{ value: boolean }>();

const emit = defineEmits(['input']);
const done = ref(false);
const errorMessages = ref<string[]>([]);
const target = ref('');
const source = ref('');
const pending = ref(false);

const { mergeAssets } = useAssets();
const { t } = useI18n();

const reset = () => {
  set(done, false);
  set(target, '');
  set(source, '');
  set(pending, false);
  set(errorMessages, []);
  get(v$).$reset();
};

const clearErrors = () => {
  const elements = get(errorMessages).length;
  for (let i = 0; i < elements; i++) {
    set(errorMessages, []);
  }
};

async function merge() {
  set(pending, true);
  const result = await mergeAssets({
    sourceIdentifier: get(source),
    targetIdentifier: get(target)
  });

  if (result.success) {
    set(done, true);
  } else {
    set(errorMessages, [
      ...get(errorMessages),
      result.message ?? t('merge_dialog.error').toString()
    ]);
    await get(v$).$validate();
  }
  set(pending, false);
}

const input = (value: boolean) => {
  emit('input', value);
  setTimeout(() => reset(), 100);
};

const rules = {
  source: {
    required: helpers.withMessage(
      t('merge_dialog.source.non_empty').toString(),
      requiredUnless(done)
    )
  },
  target: {
    required: helpers.withMessage(
      t('merge_dialog.target.non_empty').toString(),
      requiredUnless(done)
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    source,
    target
  },
  {
    $autoDirty: true,
    $externalResults: computed(() => ({ source: get(errorMessages) }))
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
        <VBtn depressed @click="input(false)">
          <span v-if="done">{{ t('common.actions.close') }}</span>
          <span v-else>
            {{ t('common.actions.cancel') }}
          </span>
        </VBtn>
        <VBtn
          v-if="!done"
          depressed
          color="primary"
          :disabled="v$.$invalid || pending"
          :loading="pending"
          @click="merge()"
        >
          {{ t('merge_dialog.merge') }}
        </VBtn>
      </template>

      <div v-if="done">{{ t('merge_dialog.done') }}</div>

      <VForm v-else :value="!v$.$invalid">
        <!-- We use `v-text-field` here instead `asset-select` -->
        <!-- because the source can be filled with unknown identifier -->
        <VTextField
          v-model="source"
          :label="t('merge_dialog.source.label')"
          :error-messages="toMessages(v$.source)"
          outlined
          :disabled="pending"
          persistent-hint
          :hint="t('merge_dialog.source_hint')"
          @focus="clearErrors()"
          @blur="v$.source.$touch()"
        />
        <VRow align="center" justify="center" class="my-4">
          <VCol cols="auto">
            <VIcon>mdi-arrow-down</VIcon>
          </VCol>
        </VRow>
        <AssetSelect
          v-model="target"
          outlined
          :error-messages="toMessages(v$.target)"
          :label="t('merge_dialog.target.label')"
          :disabled="pending"
          @focus="clearErrors()"
          @blur="v$.target.$touch()"
        />
      </VForm>
    </Card>
  </VDialog>
</template>
