<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    modelValue?: string | null;
    items: string[];
  }>(),
  {
    modelValue: null,
  },
);

const emit = defineEmits<{
  (e: 'update:model-value', value: string | null): void;
}>();

const model = useSimpleVModel(props, emit);

const { t } = useI18n();
</script>

<template>
  <RuiAutoComplete
    v-model="model"
    :label="t('nft_gallery.select_collection')"
    clearable
    hide-details
    hide-selected
    :options="items"
    variant="outlined"
    :item-height="42"
    dense
  >
    <template #selection="{ item }">
      <RuiChip
        tile
        size="sm"
        class="font-medium text-caption"
      >
        {{ item }}
      </RuiChip>
    </template>

    <template #item="{ item }">
      <RuiChip
        tile
        size="sm"
        class="font-medium text-caption my-1"
      >
        {{ item }}
      </RuiChip>
    </template>
  </RuiAutoComplete>
</template>
