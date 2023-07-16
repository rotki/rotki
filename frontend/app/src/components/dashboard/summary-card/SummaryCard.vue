<script setup lang="ts">
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
  <VCard
    :loading="isLoading"
    :class="`dashboard__summary-card__${name}`"
    class="pb-1"
  >
    <VCardTitle
      class="font-weight-medium text-capitalize px-4 pt-3 pb-0 secondary--text summary-card__header"
    >
      <CardTitle>
        <NavigatorLink :enabled="!!navigatesTo" :to="{ path: navigatesTo }">
          {{ t('summary_card.title', { name }) }}
        </NavigatorLink>
      </CardTitle>
      <VSpacer />
      <div class="d-flex align-center">
        <VTooltip v-if="canRefresh" bottom max-width="300px">
          <template #activator="{ on: tooltipOn }">
            <VBtn
              icon
              small
              :disabled="isLoading"
              color="primary"
              @click="refresh(name)"
              v-on="tooltipOn"
            >
              <VIcon small color="primary">mdi-refresh</VIcon>
            </VBtn>
          </template>
          <span>
            {{ t('summary_card.refresh_tooltip', { name }) }}
          </span>
        </VTooltip>
        <SummaryCardRefreshMenu>
          <template v-if="slots.refreshMenu" #refreshMenu>
            <slot name="refreshMenu" />
          </template>
        </SummaryCardRefreshMenu>
      </div>
    </VCardTitle>
    <VList>
      <slot />
    </VList>
  </VCard>
</template>
