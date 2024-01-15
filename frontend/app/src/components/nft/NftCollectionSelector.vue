<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    value?: string | null;
    items: string[];
  }>(),
  {
    value: null
  }
);

const emit = defineEmits<{
  (e: 'input', value: string | null): void;
}>();

const model = useSimpleVModel(props, emit);

const { t } = useI18n();
</script>

<template>
  <VAutocomplete
    v-model="model"
    :label="t('nft_gallery.select_collection')"
    single-line
    clearable
    hide-details
    hide-selected
    :items="items"
    outlined
    dense
  >
    <template #selection="{ item }">
      <RuiChip tile size="sm" class="font-medium text-caption">
        {{ item }}
      </RuiChip>
    </template>

    <template #item="{ item }">
      <RuiChip tile size="sm" class="font-medium text-caption">
        {{ item }}
      </RuiChip>
    </template>
  </VAutocomplete>
</template>
