<script setup lang="ts">
const model = defineModel<string | undefined>({ required: true });

defineProps<{
  items: string[];
}>();

const { t } = useI18n({ useScope: 'global' });
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
