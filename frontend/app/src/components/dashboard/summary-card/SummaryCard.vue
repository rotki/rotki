<script setup lang="ts">
import SummaryCardRefreshMenu from '@/components/dashboard/summary-card/SummaryCardRefreshMenu.vue';

const NavigatorLink = defineAsyncComponent(
  () => import('@/components/helper/NavigatorLink.vue')
);

withDefaults(
  defineProps<{
    name: string;
    isLoading?: boolean;
    canRefresh?: boolean;
    navigatesTo?: string;
  }>(),
  {
    isLoading: false,
    canRefresh: false,
    navigatesTo: ''
  }
);

const emit = defineEmits(['refresh']);

const refresh = (balanceSource: string) => {
  emit('refresh', balanceSource.toLowerCase());
};

const { t } = useI18n();

const slots = useSlots();
</script>

<template>
  <v-card
    :loading="isLoading"
    :class="`dashboard__summary-card__${name}`"
    class="pb-1"
  >
    <v-card-title
      class="font-weight-medium text-capitalize px-4 pt-3 pb-0 secondary--text summary-card__header"
    >
      <card-title>
        <navigator-link :enabled="!!navigatesTo" :to="{ path: navigatesTo }">
          {{ t('summary_card.title', { name }) }}
        </navigator-link>
      </card-title>
      <v-spacer />
      <div>
        <summary-card-refresh-menu
          :name="name"
          :can-refresh="canRefresh"
          :is-loading="isLoading"
          @refresh="refresh(name)"
        >
          <template v-if="slots.refreshMenu" #refreshMenu>
            <slot name="refreshMenu" />
          </template>
        </summary-card-refresh-menu>
      </div>
    </v-card-title>
    <v-list>
      <slot />
    </v-list>
  </v-card>
</template>
