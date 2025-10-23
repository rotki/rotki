<script setup lang="ts">
import type { AssetInfoWithId } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import { useAssets } from '@/composables/assets';
import { toMessages } from '@/utils/validation';

type Errors = Partial<Record<'targetIdentifier' | 'sourceIdentifier', string[]>>;

const display = defineModel<boolean>({ required: true });

const props = defineProps<{
  sourceIdentifier?: string;
  targetIdentifier?: string;
}>();

const emit = defineEmits<{
  merged: [events: { sourceIdentifier: string; targetIdentifier: string }];
}>();

const { sourceIdentifier: propSourceIdentifier, targetIdentifier: propTargetIdentifier } = toRefs(props);

const done = ref(false);
const errorMessages = ref<Errors>({});
const targetIdentifier = ref('');
const target = ref<AssetInfoWithId>();
const sourceIdentifier = ref('');
const pending = ref(false);

const { mergeAssets } = useAssets();
const { t } = useI18n({ useScope: 'global' });

const rules = {
  sourceIdentifier: {
    required: helpers.withMessage(t('merge_dialog.source.non_empty'), required),
  },
  targetIdentifier: {
    required: helpers.withMessage(t('merge_dialog.target.non_empty'), required),
  },
};

const v$ = useVuelidate(
  rules,
  {
    sourceIdentifier,
    targetIdentifier,
  },
  {
    $autoDirty: true,
    $externalResults: errorMessages,
  },
);

function reset() {
  set(done, false);
  set(targetIdentifier, '');
  set(sourceIdentifier, '');
  set(pending, false);
  set(errorMessages, {});
  get(v$).$reset();
  set(target, undefined);
}

function clearErrors() {
  set(done, false);
  set(errorMessages, {});
}

async function merge() {
  set(pending, true);
  const source = get(sourceIdentifier);
  const target = get(targetIdentifier);

  const result = await mergeAssets({
    sourceIdentifier: source,
    targetIdentifier: target,
  });

  if (result.success) {
    emit('merged', { sourceIdentifier: source, targetIdentifier: target });
    reset();
    set(done, true);
  }
  else {
    set(
      errorMessages,
      typeof result.message === 'string'
        ? ({
            sourceIdentifier: [result.message || t('merge_dialog.error')],
          } satisfies Errors)
        : result.message,
    );
    await get(v$).$validate();
  }
  set(pending, false);
}

function input(value: boolean) {
  set(display, value);
  setTimeout(() => reset(), 100);
}

const excluded = computed(() => {
  const source = get(sourceIdentifier);
  if (!source)
    return [];
  return [source];
});

watch([display, propSourceIdentifier, propTargetIdentifier], ([isDisplayed, propSourceIdentifier, propTargetIdentifier]) => {
  if (isDisplayed) {
    if (propSourceIdentifier) {
      set(sourceIdentifier, propSourceIdentifier);
    }
    if (propTargetIdentifier) {
      set(targetIdentifier, propTargetIdentifier);
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
          :hint="t('merge_dialog.source_hint')"
          @focus="clearErrors()"
          @blur="v$.sourceIdentifier.$touch()"
        />
        <div class="my-4 flex justify-center">
          <RuiIcon name="lu-arrow-down" />
        </div>
        <AssetSelect
          v-model="targetIdentifier"
          v-model:asset="target"
          outlined
          :error-messages="toMessages(v$.targetIdentifier)"
          :label="t('merge_dialog.target.label')"
          :disabled="pending"
          :excludes="excluded"
          :hint="target ? t('merge_dialog.target_hint', { identifier: target.identifier }) : ''"
          @focus="clearErrors()"
          @blur="v$.targetIdentifier.$touch()"
        />
      </form>

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
          :disabled="v$.$invalid || pending"
          :loading="pending"
          @click="merge()"
        >
          {{ t('merge_dialog.merge') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
