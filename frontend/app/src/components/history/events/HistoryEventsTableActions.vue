<script lang="ts" setup>
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { HistoryEventRequestPayload } from '@/types/history/events';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import TableStatusFilter from '@/components/helper/TableStatusFilter.vue';
import HistoryEventsExport from '@/components/history/events/HistoryEventsExport.vue';
import HistoryTableActions from '@/components/history/HistoryTableActions.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { type MatchedKeywordWithBehaviour, SavedFilterLocation, type SearchMatcher } from '@/types/filtering';
import { useRefPropVModel } from '@/utils/model';
import { checkIfDevelopment } from '@shared/utils';

const filters = defineModel<MatchedKeywordWithBehaviour<any>>('filters', { required: true });

const accounts = defineModel<BlockchainAccount<AddressData>[]>('accounts', { required: true });

const toggles = defineModel<{ customizedEventsOnly: boolean; showIgnoredAssets: boolean }>('toggles', { required: true });

withDefaults(defineProps<{
  matchers: SearchMatcher<any, any>[];
  exportParams: HistoryEventRequestPayload;
  hideAccountSelector?: boolean;
  processing?: boolean;
}>(), {
  hideAccountSelector: false,
  processing: false,
});

const emit = defineEmits<{
  'redecode': [];
  'redecode-page': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const customizedEventsOnly = useRefPropVModel(toggles, 'customizedEventsOnly');
const showIgnoredAssets = useRefPropVModel(toggles, 'showIgnoredAssets');

const { txChains } = useSupportedChains();
const txChainIds = useArrayMap(txChains, x => x.id);

const isDemoMode = import.meta.env.VITE_DEMO_MODE !== undefined;
const isDevelopment = checkIfDevelopment();

function redecodePageTransactions(): void {
  emit('redecode-page');
}
</script>

<template>
  <HistoryTableActions hide-divider>
    <template #filter>
      <TableStatusFilter>
        <div class="py-1 max-w-[16rem]">
          <RuiSwitch
            v-model="customizedEventsOnly"
            color="primary"
            class="p-4"
            hide-details
            :label="t('transactions.filter.customized_only')"
          />
          <RuiDivider />
          <RuiSwitch
            v-model="showIgnoredAssets"
            color="primary"
            class="p-4"
            hide-details
            :label="t('transactions.filter.show_ignored_assets')"
          />
        </div>
      </TableStatusFilter>
      <TableFilter
        v-model:matches="filters"
        class="min-w-[12rem] md:min-w-[24rem]"
        :matchers="matchers"
        :location="SavedFilterLocation.HISTORY_EVENTS"
      />
    </template>

    <RuiButtonGroup
      color="primary"
      :disabled="processing"
      :class="{
        '!divide-rui-grey-200 dark:!divide-rui-grey-800': processing,
      }"
    >
      <RuiButton
        class="!py-2"
        @click="emit('redecode')"
      >
        {{ t('transactions.events_decoding.redecode_all') }}
      </RuiButton>

      <RuiButton
        v-if="isDevelopment && !isDemoMode"
        class="!py-2"
        @click="redecodePageTransactions()"
      >
        {{ t('transactions.actions.redecode_page') }}
      </RuiButton>
    </RuiButtonGroup>

    <HistoryEventsExport :filters="exportParams" />

    <BlockchainAccountSelector
      v-if="!hideAccountSelector"
      v-model="accounts"
      class="w-[18rem]"
      :chains="txChainIds"
      dense
      :label="t('transactions.filter.account')"
      outlined
      multichain
      hide-chain-icon
      unique
    />
  </HistoryTableActions>
</template>
