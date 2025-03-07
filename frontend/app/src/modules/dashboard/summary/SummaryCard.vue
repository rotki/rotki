<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import NavigatorLink from '@/components/helper/NavigatorLink.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import SummaryCardRefreshMenu from './SummaryCardRefreshMenu.vue';

interface SummaryCardProps {
  name: string;
  isLoading?: boolean;
  canRefresh?: boolean;
  navigatesTo?: RouteLocationRaw;
}

withDefaults(defineProps<SummaryCardProps>(), {
  canRefresh: false,
  isLoading: false,
  navigatesTo: undefined,
});

const emit = defineEmits<{
  refresh: [source: string];
}>();

defineSlots<{
  refreshMenu: () => any;
  default: () => any;
}>();

const { t } = useI18n();
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
        <div
          v-if="canRefresh"
          class="flex items-center -my-1"
        >
          <SummaryCardRefreshMenu
            data-cy="account-balances-refresh-menu"
            :tooltip="t('summary_card.refresh_tooltip', { name })"
            :loading="isLoading"
            @refresh="emit('refresh', name.toLowerCase())"
          >
            <template
              v-if="$slots.refreshMenu"
              #refreshMenu
            >
              <slot name="refreshMenu" />
            </template>
          </SummaryCardRefreshMenu>
        </div>
      </CardTitle>
    </template>
    <div>
      <slot />
    </div>
  </RuiCard>
</template>
