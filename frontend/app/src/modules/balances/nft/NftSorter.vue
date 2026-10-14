<script setup lang="ts">
const sortByModel = defineModel<string>('sortBy', { required: true });
const sortDescModel = defineModel<boolean>('sortDesc', { required: true });

function toggleSortDesc(): void {
  set(sortDescModel, !get(sortDescModel));
}

const { t } = useI18n({ useScope: 'global' });

const sortProperties = [
  {
    text: t('common.name'),
    value: 'name',
  },
  {
    text: t('common.price'),
    value: 'price',
  },
  {
    text: t('nft_gallery.sort.collection'),
    value: 'collection',
  },
];
</script>

<template>
  <div class="flex items-center gap-1">
    <RuiMenuSelect
      v-model="sortByModel"
      class="w-40"
      :options="sortProperties"
      key-attr="value"
      text-attr="text"
      :label="t('nft_gallery.sort.by')"
      label-placement="hidden"
      hide-details
      dense
      data-testid="nft-gallery-sort"
    />
    <RuiTooltip
      :options="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          class="text-rui-text-secondary!"
          :aria-label="sortDescModel ? t('sorting_selector.desc.sort_asc_tooltip') : t('sorting_selector.desc.sort_desc_tooltip')"
          data-testid="nft-gallery-sort-direction"
          @click="toggleSortDesc()"
        >
          <RuiIcon :name="sortDescModel ? 'lu-arrow-down-z-a' : 'lu-arrow-down-a-z'" />
        </RuiButton>
      </template>
      {{ sortDescModel ? t('sorting_selector.desc.sort_asc_tooltip') : t('sorting_selector.desc.sort_desc_tooltip') }}
    </RuiTooltip>
  </div>
</template>
