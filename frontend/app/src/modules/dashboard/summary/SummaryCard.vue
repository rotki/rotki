<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import CardTitle from '@/modules/shell/components/CardTitle.vue';
import NavigatorLink from '@/modules/shell/components/NavigatorLink.vue';

interface SummaryCardProps {
  name: string;
  navigatesTo?: RouteLocationRaw;
}

const {
  name,
  navigatesTo,
} = defineProps<SummaryCardProps>();

defineSlots<{
  default: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiCard
    no-padding
    class="py-4 h-auto"
  >
    <template #custom-header>
      <CardTitle class="capitalize flex-nowrap flex justify-between gap-2 pb-2 px-6">
        <NavigatorLink
          :enabled="!!navigatesTo"
          :to="navigatesTo"
          tag="div"
          class="text-clip truncate"
          :title="t('summary_card.title', { name })"
        >
          {{ t('summary_card.title', { name }) }}
        </NavigatorLink>
      </CardTitle>
    </template>
    <div>
      <slot />
    </div>
  </RuiCard>
</template>
