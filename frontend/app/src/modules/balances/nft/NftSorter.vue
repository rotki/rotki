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
          <RuiIcon :name="sortDescModel ? 'lu-arrow-down-z-a' : 'lu-arrow-down-a-z'" />
        </RuiButton>
      </template>
      <span v-if="sortDescModel">
        {{ t('sorting_selector.desc.sort_asc_tooltip') }}
      </span>
      <span v-else>
        {{ t('sorting_selector.desc.sort_desc_tooltip') }}
      </span>
    </RuiTooltip>
    <div class="flex-1">
      <RuiMenuSelect
        v-model="sortByModel"
        :options="sortProperties"
        class="[&_fieldset]:!rounded-l-none [&_fieldset]:!border-l-0"
        key-attr="value"
        text-attr="text"
        hide-details
        variant="outlined"
        dense
      />
    </div>
  </div>
</template>
