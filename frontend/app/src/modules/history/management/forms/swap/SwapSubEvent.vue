<script setup lang="ts">
import type {
  SwapSubEventErrors,
  SwapSubEventField,
  SwapSubEventState,
} from '@/modules/history/management/forms/swap/swap-sub-event';
import EventLocationLabel from '@/modules/history/management/forms/common/EventLocationLabel.vue';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';

/**
 * The row object is mutated in place rather than replaced: the parent form keys touched-state by
 * row identity so that removing a row does not shift another row's error flags onto it.
 */
const modelValue = defineModel<SwapSubEventState>({ required: true });

const { disabled, type } = defineProps<{
  type: 'receive' | 'spend' | 'fee';
  index: number;
  disabled?: boolean;
  timestamp: number;
  location: string;
  single: boolean;
  errorMessages: SwapSubEventErrors;
}>();

const emit = defineEmits<{
  remove: [index: number];
  blur: [field: SwapSubEventField];
}>();

const { t } = useI18n({ useScope: 'global' });

const userNotesLabel = computed<string>(() => {
  if (type === 'fee') {
    return t('swap_event_form.fee_notes');
  }

  if (type === 'receive') {
    return t('swap_event_form.receive_notes');
  }

  return t('swap_event_form.spend_notes');
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
          data-testid="swap-sub-event-remove"
          :data-key="type"
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
          v-model:amount="modelValue.amount"
          v-model:asset="modelValue.asset"
          v-model:price-intent="modelValue.priceIntent"
          hide-price-fields
          :timestamp="timestamp"
          :disabled="disabled"
          :error-messages="{
            amount: errorMessages.amount,
            asset: errorMessages.asset,
          }"
          :location="location"
          :type="type"
          @blur="emit('blur', $event)"
        />

        <EventLocationLabel
          v-model="modelValue.locationLabel"
          :location="location"
          :disabled="disabled"
          :error-messages="errorMessages.locationLabel"
          @blur="emit('blur', 'locationLabel')"
        />
      </div>
    </div>
    <RuiAccordions
      :class="{
        'mx-14': !single,
      }"
    >
      <RuiAccordion
        data-testid="advanced-accordion"
        :class-names="{ header: 'py-3' }"
        eager
      >
        <template #header>
          {{ t('transactions.events.form.advanced') }}
        </template>

        <div class="py-2">
          <RuiTextArea
            v-model="modelValue.userNotes"
            prepend-icon="lu-sticky-note"
            data-testid="swap-sub-event-notes"
            :data-key="type"
            variant="outlined"
            color="primary"
            :disabled="disabled"
            max-rows="5"
            min-rows="3"
            auto-grow
            :label="userNotesLabel"
            :error-messages="errorMessages.userNotes"
            @blur="emit('blur', 'userNotes')"
          />
        </div>
      </RuiAccordion>
    </RuiAccordions>
  </div>
</template>
