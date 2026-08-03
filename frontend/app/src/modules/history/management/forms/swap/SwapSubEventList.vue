<script setup lang="ts">
import {
  emptySubEvent,
  NO_SUB_EVENT_ERRORS,
  type SwapSubEventErrors,
  type SwapSubEventField,
  type SwapSubEventState,
} from '@/modules/history/management/forms/swap/swap-sub-event';
import SwapSubEvent from '@/modules/history/management/forms/swap/SwapSubEvent.vue';

const modelValue = defineModel<SwapSubEventState[]>({ required: true });

/**
 * `errors` and `touch` are the form's own accessors, passed down rather than reimplemented, because
 * validation lives in one schema on the parent. `path` is this list's key in that schema (`spend`,
 * `receive` or `fee`), which is what turns a row index into a dotted path like `spend.1.amount`.
 */
const { path, errors, touch, type } = defineProps<{
  location: string;
  disabled?: boolean;
  timestamp: number;
  type: 'receive' | 'spend' | 'fee';
  path: string;
  errors: (path: string) => string[];
  touch: (path: string) => void;
}>();

const { t } = useI18n({ useScope: 'global' });

const label = computed<string>(() => {
  switch (type) {
    case 'receive':
      return t('backend_mappings.events.history_event_subtype.receive');
    case 'spend':
      return t('backend_mappings.events.history_event_subtype.spend');
    default:
      return t('backend_mappings.events.history_event_subtype.fee');
  }
});

const placeholder = emptySubEvent();

function fieldErrors(index: number): SwapSubEventErrors {
  return {
    amount: errors(`${path}.${index}.amount`),
    asset: errors(`${path}.${index}.asset`),
    locationLabel: errors(`${path}.${index}.locationLabel`),
    userNotes: errors(`${path}.${index}.userNotes`),
  };
}

function onBlur(index: number, field: SwapSubEventField): void {
  touch(`${path}.${index}.${field}`);
}

// Both mutate the array in place: the rows the form has already recorded touched-state against must
// keep their identity, which replacing the array would destroy.
function remove(index: number): void {
  get(modelValue).splice(index, 1);
}

function add(): void {
  get(modelValue).push(emptySubEvent());
}
</script>

<template>
  <div>
    <div class="flex py-2 mb-4 items-center gap-4">
      <div class="font-medium">
        {{ label }}
      </div>

      <RuiButton
        variant="outlined"
        color="primary"
        :data-cy="`${type}-add`"
        :disabled="disabled"
        size="sm"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-plus"
            size="14"
          />
        </template>
        {{ t('swap_event_form.add_asset') }}
      </RuiButton>
    </div>

    <SwapSubEvent
      v-if="disabled"
      :model-value="placeholder"
      :disabled="disabled"
      :error-messages="NO_SUB_EVENT_ERRORS"
      :location="location"
      :timestamp="timestamp"
      :type="type"
      :index="0"
      single
    />

    <template
      v-for="(_, index) in modelValue"
      :key="index"
    >
      <SwapSubEvent
        v-model="modelValue[index]"
        :type="type"
        :timestamp="timestamp"
        :location="location"
        :index="index"
        :disabled="disabled"
        :error-messages="fieldErrors(index)"
        :single="modelValue.length === 1"
        @remove="remove($event)"
        @blur="onBlur(index, $event)"
      />

      <RuiDivider
        v-if="index !== modelValue.length - 1"
        class="mb-6 mt-2 mx-14"
      />
    </template>
  </div>
</template>
