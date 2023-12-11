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
  <RuiCard class="py-4 h-auto">
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
        <div v-if="canRefresh" class="flex items-center">
          <SummaryCardRefreshMenu
            data-cy="account-balances-refresh-menu"
            :tooltip="t('summary_card.refresh_tooltip', { name })"
            :loading="isLoading"
            @refresh="refresh(name)"
          >
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
