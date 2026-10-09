<script setup lang="ts">
import { useLocations } from '@/modules/core/common/use-locations';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

const { exchange } = defineProps<{ exchange: string }>();

const emit = defineEmits<{ refresh: [exchange: string] }>();

const { t } = useI18n({ useScope: 'global' });
const { getExchangeName } = useLocations();
const { useIsActive } = useTaskCenter();

// each exchange's query is its own activity, so the row spins only for its own refresh
const loading = useIsActive(ActivityKind.EXCHANGE_BALANCES, exchange);
</script>

<template>
  <RuiButton
    variant="list"
    :disabled="loading"
    :aria-label="t('exchange_balances.refresh_menu.exchange', { exchange: getExchangeName(exchange) })"
    data-testid="refresh-exchange-menu-item"
    :data-exchange="exchange"
    @click="emit('refresh', exchange)"
  >
    <template #prepend>
      <LocationIcon
        :item="exchange"
        icon
        size="20px"
      />
    </template>
    <span class="flex-1 text-left">{{ getExchangeName(exchange) }}</span>
    <template #append>
      <RuiProgress
        v-if="loading"
        circular
        variant="indeterminate"
        size="16"
        thickness="2"
        color="primary"
      />
      <RuiIcon
        v-else
        name="lu-refresh-ccw"
        size="16"
        class="text-rui-text-secondary"
      />
    </template>
  </RuiButton>
</template>
