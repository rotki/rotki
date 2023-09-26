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
  <RuiCard
    :loading="isLoading"
    :class="`dashboard__summary-card__${name}`"
    class="pb-6 pt-4 h-auto"
  >
    <template #custom-header>
      <CardTitle
        class="text-capitalize summary-card__header flex-nowrap flex justify-between gap-2 pb-4 px-6"
      >
        <NavigatorLink
          :enabled="!!navigatesTo"
          :to="{ path: navigatesTo }"
          tag="div"
          class="text-clip truncate"
          :title="t('summary_card.title', { name })"
        >
          {{ t('summary_card.title', { name }) }}
        </NavigatorLink>
        <div class="flex items-center">
          <RuiTooltip
            v-if="canRefresh"
            open-delay="400"
            :popper="{ placement: 'bottom', offsetDistance: 0 }"
            max-width="300px"
          >
            <template #activator="{ on: tooltipOn }">
              <RuiButton
                icon
                variant="text"
                :loading="isLoading"
                color="primary"
                @click="refresh(name)"
                v-on="tooltipOn"
              >
                <RuiIcon color="primary" name="restart-line" />
              </RuiButton>
            </template>
            <span>
              {{ t('summary_card.refresh_tooltip', { name }) }}
            </span>
          </RuiTooltip>
          <SummaryCardRefreshMenu>
            <template v-if="slots.refreshMenu" #refreshMenu>
              <slot name="refreshMenu" />
            </template>
          </SummaryCardRefreshMenu>
        </div>
      </CardTitle>
    </template>
    <VList class="py-0 -m-4">
      <slot />
    </VList>
  </RuiCard>
</template>
