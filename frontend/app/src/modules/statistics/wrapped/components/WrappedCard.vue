<script setup lang="ts" generic="T extends object">
import WrappedItem from '@/components/wrapped/WrappedItem.vue';

const props = defineProps<{
  items: T[];
}>();

const { t } = useI18n({ useScope: 'global' });

const INITIAL_LENGTH = 5;

const showMoreButton = computed<boolean>(() => props.items.length > INITIAL_LENGTH);

const showAll = ref<boolean>(false);

const itemsToUse = computed<T[]>(() => {
  const items = props.items;
  if (get(showAll))
    return items;

  return items.slice(0, INITIAL_LENGTH);
});
</script>

<template>
  <RuiCard
    no-padding
    variant="outlined"
    class="overflow-hidden"
    content-class="divide-y divide-rui-grey-300 dark:divide-rui-grey-800 bg-rui-grey-50 dark:bg-rui-grey-900"
  >
    <div class="flex px-4 py-3 gap-2 items-center bg-gradient-to-b from-transparent to-rui-primary/[0.05]">
      <div class="flex items-center justify-center size-6 shrink-0 bg-rui-primary-lighter/[0.2] dark:bg-rui-primary-darker/[0.2] rounded-full overflow-hidden">
        <slot name="header-icon" />
      </div>
      <h3 class="text-sm font-medium ">
        <slot name="header" />
      </h3>
    </div>
    <WrappedItem
      v-for="(item, index) in itemsToUse"
      :key="index"
    >
      <template #label>
        <slot
          name="label"
          v-bind="{ item, index }"
        >
          {{ 'label' in item ? item.label : item }}
        </slot>
      </template>
      <template #value>
        <slot
          name="value"
          v-bind="{ item, index }"
        >
          {{ 'value' in item ? item.value : item }}
        </slot>
      </template>
    </WrappedItem>
    <div
      v-if="showMoreButton"
      class="px-4 h-[3.25rem] text-rui-primary cursor-pointer flex items-center text-sm"
      @click="showAll = !showAll"
    >
      {{ showAll ? t('liquity_statistic.view.hide') : t('liquity_statistic.view.show') }}
    </div>
  </RuiCard>
</template>
