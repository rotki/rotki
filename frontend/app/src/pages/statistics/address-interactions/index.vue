<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { msg } from '@/message-key';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import AddressInteractionGraph from '@/modules/statistics/address-interactions/AddressInteractionGraph.vue';
import { useAddressInteractions } from '@/modules/statistics/address-interactions/use-address-interactions';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.statistics_sub.address_interactions'), icon: 'lu-network', parent: '/statistics/', order: 50, drawer: 'statistics-address-interactions' },
    scrollsItself: true,
  },
});

const { t } = useI18n({ useScope: 'global' });
const { error, interactions, loading, refresh } = useAddressInteractions();

onMounted(() => startPromise(refresh()));
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.statistics'), t('navigation_menu.statistics_sub.address_interactions')]"
    child
    class="w-full px-4"
  >
    <template #buttons>
      <RuiButton
        variant="outlined"
        color="primary"
        :loading="loading"
        data-testid="address-interactions-refresh"
        @click="refresh()"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-cw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>
    </template>
    <RuiAlert
      v-if="error"
      type="error"
      data-testid="address-interactions-error"
    >
      {{ t('address_interactions.error') }} {{ error }}
    </RuiAlert>
    <RuiProgress
      v-if="loading && interactions.length === 0"
      variant="indeterminate"
      color="primary"
      :aria-label="t('address_interactions.loading')"
    />
    <AddressInteractionGraph
      v-if="interactions.length > 0"
      :interactions="interactions"
      :loading="loading"
    />
    <RuiCard
      v-else-if="!loading && !error"
      data-testid="address-interactions-empty"
    >
      <p class="text-rui-text-secondary">
        {{ t('address_interactions.empty') }}
      </p>
      <RouterLink
        :to="{ name: '/history/events/' }"
        class="text-rui-primary"
      >
        {{ t('address_interactions.view_history') }}
      </RouterLink>
    </RuiCard>
  </TablePageLayout>
</template>
