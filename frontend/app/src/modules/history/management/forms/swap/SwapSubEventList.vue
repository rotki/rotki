<script setup lang="ts">
import type { SwapSubEventModel } from '@/types/history/events';
import SwapSubEvent from '@/modules/history/management/forms/swap/SwapSubEvent.vue';

const modelValue = defineModel<SwapSubEventModel[]>({ required: true });

const props = withDefaults(defineProps<{
  location: string;
  disabled?: boolean;
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
</script>

<template>
  <div>
    <div class="flex py-2 mb-4 items-center">
      <div class="font-medium grow">
        {{ label }}
      </div>

      <RuiButton
        variant="default"
        color="primary"
        :data-cy="`${type}-add`"
        :disabled="disabled"
        @click="add()"
      >
        {{ t('common.actions.add') }}
      </RuiButton>
    </div>

    <SwapSubEvent
      v-if="disabled"
      :model-value="placeholder"
      :disabled="disabled"
      :location="location"
      :type="type"
      :index="0"
      single
    />

    <template
      v-for="(entry, index) in modelValue"
      :key="index"
    >
      <SwapSubEvent
        v-model="modelValue[index]"
        :type="type"
        :location="location"
        :index="index"
        :single="modelValue.length === 1"
        @remove="remove($event)"
      />

      <RuiDivider
        v-if="index !== modelValue.length - 1"
        class="mb-6 mt-2 mx-8"
      />
    </template>
  </div>
</template>
