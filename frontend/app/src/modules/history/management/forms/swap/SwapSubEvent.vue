<script setup lang="ts">
import type { SwapSubEventModel } from '@/types/history/events/schemas';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import EventLocationLabel from '@/modules/history/management/forms/common/EventLocationLabel.vue';
import ToggleLocationLink from '@/modules/history/management/forms/common/ToggleLocationLink.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { isEqual, pick } from 'es-toolkit';

const modelValue = defineModel<SwapSubEventModel>({ required: true });

const props = withDefaults(defineProps<{
  type: 'receive' | 'spend' | 'fee';
  index: number;
  disabled?: boolean;
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

const evmChain = ref<string>();

const { t } = useI18n({ useScope: 'global' });
const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const amountLabel = computed<string>(() => {
  switch (props.type) {
    case 'receive':
      return t('swap_event_form.receive_amount');
    case 'spend':
      return t('swap_event_form.spend_amount');
    default:
      return t('transactions.events.form.fee_amount.label');
  }
});

const assetLabel = computed<string>(() => {
  switch (props.type) {
    case 'receive':
      return t('swap_event_form.receive_asset');
    case 'spend':
      return t('swap_event_form.spend_asset');
    default:
      return t('transactions.events.form.fee_asset.label');
  }
});

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
</script>

<template>
  <div>
    <div class="flex items-center">
      <div
        v-if="!single"
        class="font-medium p-4"
      >
        {{ index + 1 }}
      </div>

      <div class="grow">
        <div class="grid md:grid-cols-2 gap-4">
          <AmountInput
            v-model="amount"
            clearable
            variant="outlined"
            :data-cy="`${type}-amount`"
            :disabled="disabled"
            :label="amountLabel"
            :error-messages="toMessages(v$.amount)"
            @blur="v$.amount.$touch()"
          />
          <div class="flex">
            <AssetSelect
              v-model="asset"
              outlined
              clearable
              :evm-chain="evmChain"
              :disabled="disabled"
              :data-cy="`${type}-asset`"
              :label="assetLabel"
              :error-messages="toMessages(v$.asset)"
              @blur="v$.asset.$touch()"
            />
            <ToggleLocationLink
              v-model="evmChain"
              :location="location"
            />
          </div>
        </div>

        <EventLocationLabel
          v-model="locationLabel"
          :location="location"
          :disabled="disabled"
          :error-messages="toMessages(v$.locationLabel)"
          @blur="v$.locationLabel.$touch()"
        />
      </div>

      <div
        v-if="!single"
        class="px-4"
      >
        <RuiButton
          variant="text"
          :disabled="disabled"
          :data-cy="`${type}-remove`"
          icon
          @click="emit('remove', index)"
        >
          <RuiIcon name="lu-trash-2" />
        </RuiButton>
      </div>
    </div>
    <RuiAccordions
      :class="{
        'mx-8': !single,
      }"
    >
      <RuiAccordion
        data-cy="advanced-accordion"
        header-class="py-4"
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
