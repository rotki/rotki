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

const emit = defineEmits<{
  (e: 'refresh', balanceSource: string): void;
}>();

const refresh = (balanceSource: string) => {
  emit('refresh', balanceSource.toLowerCase());
};

const { t } = useI18n();

const slots = useSlots();
</script>

<template>
  <RuiCard :loading="isLoading" class="pb-6 pt-4 h-auto">
    <template #custom-header>
      <CardTitle
        class="text-capitalize flex-nowrap flex justify-between gap-2 pb-2 px-6"
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
            <template #activator>
              <RuiButton
                icon
                variant="text"
                :loading="isLoading"
                color="primary"
                @click="refresh(name)"
              >
                <RuiIcon color="primary" name="restart-line" />
              </RuiButton>
            </template>
            <span>
              {{ t('summary_card.refresh_tooltip', { name }) }}
            </span>
          </RuiTooltip>
          <SummaryCardRefreshMenu v-if="slots.refreshMenu">
            <template #refreshMenu>
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
