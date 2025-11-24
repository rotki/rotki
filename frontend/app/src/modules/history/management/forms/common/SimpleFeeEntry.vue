<script setup lang="ts">
import type { FeeEntry } from '@/types/history/events/schemas';
import useVuelidate from '@vuelidate/core';
import { isEqual } from 'es-toolkit';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<FeeEntry>({ required: true });

const props = withDefaults(defineProps<{
  index: number;
  disabled?: boolean;
  single: boolean;
  location?: string;
}>(), {
  disabled: false,
  location: undefined,
});

const emit = defineEmits<{
  remove: [index: number];
}>();

const amount = ref<string>('');
const asset = ref<string>('');
const chain = ref<string>();

const { t } = useI18n({ useScope: 'global' });
const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const rules = computed(() => (props.disabled
  ? {
      amount: {},
      asset: {},
    }
  : {
      amount: commonRules.createRequiredAmountRule(),
      asset: commonRules.createRequiredAssetRule(),
    }));

const v$ = useVuelidate(
  rules,
  {
    amount,
    asset,
  },
  {
    $autoDirty: true,
  },
);

function updateModel(): void {
  set(modelValue, {
    amount: get(amount),
    asset: get(asset),
  });
}

watch(modelValue, (model, oldModel) => {
  if (isEqual(model, oldModel))
    return;

  set(amount, model.amount);
  set(asset, model.asset);
}, { immediate: true });

watch(amount, (amount, oldAmount) => {
  if (amount === oldAmount)
    return;
  updateModel();
});

watch(asset, (asset, oldAsset) => {
  if (asset === oldAsset)
    return;
  updateModel();
});

watch(() => props.location, (newLocation) => {
  if (newLocation)
    set(chain, newLocation);
});
</script>

<template>
  <div class="group/fee">
    <div class="flex items-center gap-4">
      <template v-if="!single">
        <div
          class="group-hover/fee:hidden font-medium border border-rui-grey-300 dark:border-rui-grey-800 rounded-full size-10 flex items-center justify-center -mt-5"
        >
          {{ index + 1 }}
        </div>
        <RuiButton
          class="hidden group-hover/fee:flex size-10 -mt-5"
          variant="outlined"
          :disabled="disabled"
          data-cy="fee-remove"
          icon
          color="error"
          @click="emit('remove', index)"
        >
          <RuiIcon
            name="lu-trash-2"
            size="14"
          />
        </RuiButton>
      </template>

      <div class="grow grid md:grid-cols-2 gap-4">
        <AmountInput
          v-model="amount"
          variant="outlined"
          data-cy="fee-amount"
          :disabled="disabled"
          :label="t('common.amount')"
          :error-messages="toMessages(v$.amount)"
          @blur="v$.amount.$touch()"
        />
        <AssetSelect
          v-model="asset"
          outlined
          show-ignored
          :disabled="disabled"
          data-cy="fee-asset"
          :chain="chain"
          :error-messages="toMessages(v$.asset)"
          @blur="v$.asset.$touch()"
        />
      </div>
    </div>
  </div>
</template>
