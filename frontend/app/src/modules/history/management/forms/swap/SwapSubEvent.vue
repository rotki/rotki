<script setup lang="ts">
import type { ActionStatus } from '@/types/action';
import type { ValidationErrors } from '@/types/api/errors';
import type { SwapSubEventModel } from '@/types/history/events/schemas';
import useVuelidate from '@vuelidate/core';
import { isEqual, pick } from 'es-toolkit';
import EventLocationLabel from '@/modules/history/management/forms/common/EventLocationLabel.vue';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<SwapSubEventModel>({ required: true });

const props = withDefaults(defineProps<{
  type: 'receive' | 'spend' | 'fee';
  index: number;
  disabled?: boolean;
  timestamp: number;
  location: string;
  single: boolean;
}>(), {
  disabled: false,
});

const emit = defineEmits<{
  remove: [index: number];
}>();

const amount = ref<string>('');
const asset = ref<string>('');
const locationLabel = ref<string>('');
const userNotes = ref<string>('');

const assetPriceForm = useTemplateRef<InstanceType<typeof HistoryEventAssetPriceForm>>('assetPriceForm');

const { t } = useI18n({ useScope: 'global' });
const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const rules = computed(() => (props.disabled
  ? {
      amount: {},
      asset: {},
      locationLabel: {},
      userNotes: {},
    }
  : {
      amount: commonRules.createRequiredAmountRule(),
      asset: commonRules.createRequiredAssetRule(),
      locationLabel: commonRules.createValidEthAddressRule(),
      userNotes: commonRules.createExternalValidationRule(),
    }));

const v$ = useVuelidate(
  rules,
  {
    amount,
    asset,
    locationLabel,
    userNotes,
  },
  {
    $autoDirty: true,
  },
);

function updateModel() {
  const updatedModel: SwapSubEventModel = pick(get(modelValue), ['identifier', 'amount', 'asset']);

  if (get(amount) !== updatedModel.amount) {
    updatedModel.amount = get(amount);
  }
  if (get(asset) !== updatedModel.asset) {
    updatedModel.asset = get(asset);
  }

  if (get(locationLabel)) {
    updatedModel.locationLabel = get(locationLabel);
  }
  else {
    delete updatedModel.locationLabel;
  }

  if (get(userNotes)) {
    updatedModel.userNotes = get(userNotes);
  }
  else {
    delete updatedModel.userNotes;
  }

  set(modelValue, updatedModel);
}

watch(modelValue, (model, oldModel) => {
  if (isEqual(model, oldModel))
    return;

  set(amount, model.amount);
  set(asset, model.asset);
  set(locationLabel, model.locationLabel ?? '');
  set(userNotes, model.userNotes ?? '');
}, { immediate: true });

watch(amount, (amount, oldAmount) => {
  if (amount === oldAmount) {
    return;
  }
  updateModel();
});

watch(asset, (asset, oldAsset) => {
  if (asset === oldAsset) {
    return;
  }
  updateModel();
});

watch(locationLabel, (locationLabel, oldLocationLabel) => {
  if (locationLabel === oldLocationLabel) {
    return;
  }
  updateModel();
});

watch(userNotes, (userNotes, oldUserNotes) => {
  if (userNotes === oldUserNotes) {
    return;
  }
  updateModel();
});

async function submitPrice(): Promise<ActionStatus<ValidationErrors | string> | undefined> {
  return await get(assetPriceForm)?.submitPrice();
}

defineExpose({
  submitPrice,
});
</script>

<template>
  <div class="group/asset">
    <div class="flex items-center gap-4">
      <template v-if="!single">
        <div
          v-if="!single"
          class="group-hover/asset:hidden font-medium border border-rui-grey-300 dark:border-rui-grey-800 rounded-full size-10 flex items-center justify-center"
        >
          {{ index + 1 }}
        </div>
        <RuiButton
          class="hidden group-hover/asset:flex size-10"
          variant="outlined"
          :disabled="disabled"
          :data-cy="`${type}-remove`"
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

      <div class="grow">
        <HistoryEventAssetPriceForm
          ref="assetPriceForm"
          v-model:amount="amount"
          v-model:asset="asset"
          hide-price-fields
          :timestamp="timestamp"
          :v$="v$"
          :location="location"
          :type="type"
        />

        <EventLocationLabel
          v-model="locationLabel"
          :location="location"
          :disabled="disabled"
          :error-messages="toMessages(v$.locationLabel)"
          @blur="v$.locationLabel.$touch()"
        />
      </div>
    </div>
    <RuiAccordions
      :class="{
        'mx-14': !single,
      }"
    >
      <RuiAccordion
        data-cy="advanced-accordion"
        header-class="py-3"
        eager
      >
        <template #header>
          {{ t('transactions.events.form.advanced') }}
        </template>

        <div class="py-2">
          <RuiTextArea
            v-model="userNotes"
            prepend-icon="lu-sticky-note"
            :data-cy="`${type}-notes`"
            variant="outlined"
            color="primary"
            :disabled="disabled"
            max-rows="5"
            min-rows="3"
            auto-grow
            :label="t('swap_event_form.spend_notes')"
            :error-messages="toMessages(v$.userNotes)"
            @blur="v$.userNotes.touch()"
          />
        </div>
      </RuiAccordion>
    </RuiAccordions>
  </div>
</template>
