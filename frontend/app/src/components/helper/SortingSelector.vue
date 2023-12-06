<script setup lang="ts">
const props = defineProps<{
  sortBy: string;
  sortDesc: boolean;
  sortProperties: { text: string; value: string }[];
}>();

const emit = defineEmits<{
  (e: 'update:sort-by', sortBy: string): void;
  (e: 'update:sort-desc', sortDesc: boolean): void;
}>();

const { sortDesc: sortDescending } = toRefs(props);
const updateSortBy = (value: string) => {
  emit('update:sort-by', value);
};
const updateSortDesc = () => {
  emit('update:sort-desc', !get(sortDescending));
};

const { t } = useI18n();
</script>

<template>
  <div class="flex">
    <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
      <template #activator>
        <RuiButton
          variant="text"
          icon
          class="!p-2"
          color="primary"
          @click="updateSortDesc()"
        >
          <RuiIcon :name="sortDescending ? 'sort-desc' : 'sort-asc'" />
        </RuiButton>
      </template>
      <span v-if="sortDescending">
        {{ t('sorting_selector.desc.sort_asc_tooltip') }}
      </span>
      <span v-else>{{ t('sorting_selector.desc.sort_desc_tooltip') }}</span>
    </RuiTooltip>
    <div class="flex-1 ml-2 bg-white dark:bg-rui-grey-900">
      <VSelect
        :value="sortBy"
        hide-details
        single-line
        dense
        outlined
        :items="sortProperties"
        @input="updateSortBy($event)"
      />
    </div>
  </div>
</template>
