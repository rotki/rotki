<script setup lang="ts">
import type { ComponentPublicInstance } from 'vue';
import type { SwapSubEventModel } from '@/types/history/events/schemas';
import SwapSubEvent from '@/modules/history/management/forms/swap/SwapSubEvent.vue';

const modelValue = defineModel<SwapSubEventModel[]>({ required: true });

const props = withDefaults(defineProps<{
  location: string;
  disabled?: boolean;
  timestamp: number;
  solana?: boolean;
  type: 'receive' | 'spend' | 'fee';
}>(), {
  disabled: false,
});

const { t } = useI18n({ useScope: 'global' });

const label = computed<string>(() => {
  switch (props.type) {
    case 'receive':
      return t('backend_mappings.events.history_event_subtype.receive');
    case 'spend':
      return t('backend_mappings.events.history_event_subtype.spend');
    default:
      return t('backend_mappings.events.history_event_subtype.fee');
  }
});

const placeholder: SwapSubEventModel = {
  amount: '',
  asset: '',
};

function remove(index: number) {
  const newModelValue = [...get(modelValue)];
  newModelValue.splice(index, 1);
  set(modelValue, newModelValue);
}

function add() {
  set(modelValue, [...get(modelValue), { amount: '', asset: '' }]);
}

interface SwapSubEventRef extends ComponentPublicInstance {
  submitPrice: () => Promise<any>;
}

const subEventRefs = ref<SwapSubEventRef[]>([]);

function isSwapSubEventComponent(el: Element | ComponentPublicInstance | null): el is SwapSubEventRef {
  return el !== null && typeof el === 'object' && '$el' in el && 'submitPrice' in el;
}

function setSubEventRef(el: Element | ComponentPublicInstance | null, index: number) {
  if (isSwapSubEventComponent(el)) {
    subEventRefs.value[index] = el;
  }
}

function getSubEventRefs(): SwapSubEventRef[] {
  return get(subEventRefs).filter(Boolean);
}

defineExpose({
  getSubEventRefs,
});
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
      :location="location"
      :timestamp="timestamp"
      :type="type"
      :index="0"
      single
      :solana="solana"
    />

    <template
      v-for="(_, index) in modelValue"
      :key="index"
    >
      <SwapSubEvent
        :ref="(el) => setSubEventRef(el, index)"
        v-model="modelValue[index]"
        :type="type"
        :timestamp="timestamp"
        :location="location"
        :index="index"
        :single="modelValue.length === 1"
        :solana="solana"
        @remove="remove($event)"
      />

      <RuiDivider
        v-if="index !== modelValue.length - 1"
        class="mb-6 mt-2 mx-14"
      />
    </template>
  </div>
</template>
