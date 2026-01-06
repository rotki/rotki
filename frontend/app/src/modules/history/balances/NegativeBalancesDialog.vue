<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { NegativeBalanceDetectedData } from '@/modules/messaging/types/status-types';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { Routes } from '@/router/routes';

const modelValue = defineModel<boolean>({ required: true });

const props = defineProps<{
  negativeBalances: NegativeBalanceDetectedData[];
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const lastRunTs = computed<number | undefined>(() => {
  const balances = props.negativeBalances;
  if (balances.length === 0)
    return undefined;
  return balances[0].lastRunTs ?? undefined;
});

const headers = computed<DataTableColumn<NegativeBalanceDetectedData>[]>(() => [
  {
    key: 'asset',
    label: t('historical_balances.negative_balances.asset'),
  },
  {
    key: 'balanceBefore',
    label: t('historical_balances.negative_balances.balance_before'),
  },
  {
    key: 'actions',
    label: '',
  },
]);

async function navigateToEvent(row: NegativeBalanceDetectedData): Promise<void> {
  set(modelValue, false);
  await router.push({
    path: `${Routes.HISTORY_EVENTS}`,
    query: {
      groupIdentifiers: row.groupIdentifier,
      highlightedIdentifier: row.eventIdentifier.toString(),
    },
  });
}
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="800"
  >
    <RuiCard>
      <template #custom-header>
        <div class="flex items-center justify-between w-full px-4 pt-2">
          <CardTitle>
            {{ t('historical_balances.negative_balances.dialog_title') }}
          </CardTitle>
          <RuiButton
            variant="text"
            :icon="true"
            @click="modelValue = false"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </div>
      </template>

      <div
        v-if="lastRunTs"
        class="mb-4 text-body-2 text-rui-text-secondary"
      >
        {{ t('historical_balances.negative_balances.last_run') }}
        <DateDisplay :timestamp="lastRunTs" />
      </div>

      <RuiDataTable
        :cols="headers"
        :rows="negativeBalances"
        row-attr="eventIdentifier"
        outlined
        dense
        class="table-inside-dialog"
      >
        <template #item.asset="{ row }">
          <AssetDetails
            :asset="row.asset"
            :dense="true"
          />
        </template>
        <template #item.balanceBefore="{ row }">
          <AmountDisplay
            :value="row.balanceBefore"
            :asset="row.asset"
          />
        </template>
        <template #item.actions="{ row }">
          <RuiTooltip
            :popper="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              <RuiButton
                variant="text"
                size="sm"
                color="primary"
                @click="navigateToEvent(row)"
              >
                <template #prepend>
                  <RuiIcon
                    name="lu-external-link"
                    size="16"
                  />
                </template>
                {{ t('historical_balances.negative_balances.view_event') }}
              </RuiButton>
            </template>
            {{ t('historical_balances.negative_balances.view_event_tooltip') }}
          </RuiTooltip>
        </template>
      </RuiDataTable>
    </RuiCard>
  </RuiDialog>
</template>
