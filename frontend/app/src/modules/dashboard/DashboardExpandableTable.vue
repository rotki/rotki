<script setup lang="ts">
import CardTitle from '@/modules/shell/components/CardTitle.vue';

const { count } = defineProps<{
  /** Rows the table holds, shown beside the title. */
  count?: number;
}>();

defineSlots<{
  title: () => any;
  /** Buttons that act on the whole table, kept after the title so every title starts at the same edge. */
  titleActions: () => any;
  details: () => any;
  shortDetails: () => any;
  default: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const expanded = ref<boolean>(true);

const panel = computed<number>(() => (get(expanded) ? 0 : -1));
</script>

<template>
  <RuiCard
    :class-names="{ content: '!p-0' }"
    class="[&_th]:!py-1 [&_th]:normal-case [&_[data-id=column-text]]:text-xs [&_[data-id=column-text]]:!text-rui-text-secondary [&_[data-sorted]_[data-id=column-text]]:!text-rui-text [&_td]:tabular-nums"
  >
    <template #custom-header>
      <div class="flex justify-between items-center flex-wrap py-2 px-4 gap-x-4 gap-y-2">
        <CardTitle class="gap-x-2.5">
          <slot name="title" />
          <span
            v-if="count !== undefined"
            class="text-body-2 text-rui-text-secondary"
            data-testid="dashboard-table-count"
          >
            {{ count }}
          </span>
          <slot name="titleActions" />
        </CardTitle>

        <div class="flex items-center gap-1 grow justify-end min-h-8">
          <slot
            v-if="expanded"
            name="details"
          />
          <slot
            v-else
            name="shortDetails"
          />
          <RuiButton
            variant="text"
            icon
            size="sm"
            class="ml-1"
            :aria-label="expanded ? t('dashboard.table.collapse') : t('dashboard.table.expand')"
            :aria-expanded="expanded"
            data-testid="dashboard-table-toggle"
            @click="expanded = !expanded"
          >
            <RuiIcon
              :name="expanded ? 'lu-chevron-up' : 'lu-chevron-down'"
              size="18"
            />
          </RuiButton>
        </div>
      </div>
    </template>
    <RuiAccordions :model-value="panel">
      <RuiAccordion eager>
        <template #default>
          <slot />
        </template>
      </RuiAccordion>
    </RuiAccordions>
  </RuiCard>
</template>
