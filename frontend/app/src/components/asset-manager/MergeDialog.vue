<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
import type { AssetInfoWithId } from '@/types/asset';

type Errors = Partial<
  Record<'targetIdentifier' | 'sourceIdentifier', string[]>
>;

const props = defineProps<{ value: boolean }>();

const emit = defineEmits<{ (e: 'input', value: boolean): void }>();

const display = useSimpleVModel(props, emit);

const done = ref(false);
const errorMessages = ref<Errors>({});
const targetIdentifier = ref('');
const target = ref<AssetInfoWithId>();
const sourceIdentifier = ref('');
const pending = ref(false);

const { mergeAssets } = useAssets();
const { t } = useI18n();

const rules = {
  sourceIdentifier: {
    required: helpers.withMessage(
      t('merge_dialog.source.non_empty').toString(),
      required,
    ),
  },
  targetIdentifier: {
    required: helpers.withMessage(
      t('merge_dialog.target.non_empty').toString(),
      required,
    ),
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
  const result = await mergeAssets({
    sourceIdentifier: get(sourceIdentifier),
    targetIdentifier: get(targetIdentifier),
  });

  if (result.success) {
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
  emit('input', value);
  setTimeout(() => reset(), 100);
}
</script>

<template>
  <RuiDialog
    v-model="display"
    max-width="500"
  >
    <AppBridge>
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
            <RuiIcon name="arrow-down-line" />
          </div>
          <AssetSelect
            v-model="targetIdentifier"
            outlined
            :error-messages="toMessages(v$.targetIdentifier)"
            :label="t('merge_dialog.target.label')"
            :disabled="pending"
            :asset.sync="target"
            :excludes="sourceIdentifier ? [sourceIdentifier] : []"
            :hint="target ? t('merge_dialog.target_hint', { identifier: target.identifier }) : ''"
            persistent-hint
            @focus="clearErrors()"
            @blur="v$.targetIdentifier.$touch()"
          />
        </form>

        <RuiAlert
          v-if="done"
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
    </AppBridge>
  </RuiDialog>
</template>
