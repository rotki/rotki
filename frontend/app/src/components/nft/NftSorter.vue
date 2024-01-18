<script setup lang="ts">
const props = defineProps<{
  sortBy: string;
  sortDesc: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:sort-by', sortBy: string): void;
  (e: 'update:sort-desc', sortDesc: boolean): void;
}>();

const { sortDesc: sortDescending } = toRefs(props);

function toggleSortDesc() {
  emit('update:sort-desc', !get(sortDescending));
}

const sortByModel = useKebabVModel(props, 'sortBy', emit);

const { t } = useI18n();

const sortProperties = [
  {
    text: t('common.name'),
    value: 'name',
  },
  {
    text: t('common.price'),
    value: 'priceUsd',
  },
  {
    text: t('nft_gallery.sort.collection'),
    value: 'collection',
  },
];
</script>

<template>
  <div class="flex">
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          color="secondary"
          class="rounded-r-none"
          @click="toggleSortDesc()"
        >
          <RuiIcon :name="sortDescending ? 'sort-desc' : 'sort-asc'" />
        </RuiButton>
      </template>
      <span v-if="sortDescending">
        {{ t('sorting_selector.desc.sort_asc_tooltip') }}
      </span>
      <span v-else>
        {{ t('sorting_selector.desc.sort_desc_tooltip') }}
      </span>
    </RuiTooltip>
    <div class="flex-1">
      <VSelect
        v-model="sortByModel"
        class="!rounded-l-none border-l-0"
        hide-details
        single-line
        dense
        outlined
        :items="sortProperties"
      />
    </div>
  </div>
</template>
