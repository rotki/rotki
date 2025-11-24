<script setup lang="ts">
import type { FeeEntry } from '@/types/history/events/schemas';
import SimpleFeeEntry from '@/modules/history/management/forms/common/SimpleFeeEntry.vue';

const modelValue = defineModel<FeeEntry[]>({ required: true });

withDefaults(defineProps<{
  disabled?: boolean;
  location?: string;
}>(), {
  disabled: false,
  location: undefined,
});

const { t } = useI18n({ useScope: 'global' });

const placeholder: FeeEntry = {
  amount: '',
  asset: '',
};

function remove(index: number): void {
  const newModelValue = [...get(modelValue)];
  newModelValue.splice(index, 1);
  set(modelValue, newModelValue);
}

function add(): void {
  set(modelValue, [...get(modelValue), { amount: '', asset: '' }]);
}
</script>

<template>
  <div>
    <div class="flex py-2 mb-4 items-center gap-4">
      <div class="font-medium">
        {{ t('backend_mappings.events.history_event_subtype.fee') }}
      </div>

      <RuiButton
        variant="outlined"
        color="primary"
        data-cy="fee-add"
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

    <SimpleFeeEntry
      v-if="disabled"
      :model-value="placeholder"
      :disabled="disabled"
      :location="location"
      :index="0"
      single
    />

    <template
      v-for="(_, index) in modelValue"
      :key="index"
    >
      <SimpleFeeEntry
        v-model="modelValue[index]"
        :index="index"
        :disabled="disabled"
        :single="modelValue.length === 1"
        :location="location"
        @remove="remove($event)"
      />

      <RuiDivider
        v-if="index !== modelValue.length - 1"
        class="mb-6 mt-2 mx-14"
      />
    </template>
  </div>
</template>
