<template>
  <v-container class="pb-12">
    <v-row align="center" class="mt-12">
      <v-col cols="auto">
        <location-icon :item="location" icon size="48px" no-padding />
      </v-col>
      <v-col class="d-flex flex-column" cols="auto">
        <span class="text-h5 font-weight-medium">{{ location.name }}</span>
      </v-col>
    </v-row>
    <location-value-row class="mt-8" :identifier="identifier" />
    <location-assets class="mt-8" :identifier="identifier" />
    <div v-if="showTrades" class="mt-8">
      <closed-trades :location-overview="identifier" />
    </div>
    <div v-if="showAssetMovements" class="mt-8">
      <deposits-withdrawals-content :location-overview="identifier" />
    </div>
    <div v-if="showLedgerActions" class="mt-8">
      <ledger-action-content :location-overview="identifier" />
    </div>
  </v-container>
</template>
<script setup lang="ts">
import ClosedTrades from '@/components/history/ClosedTrades.vue';
import DepositsWithdrawalsContent from '@/components/history/deposits-withdrawals/DepositsWithdrawalsContent.vue';
import LedgerActionContent from '@/components/history/ledger-actions/LedgerActionContent.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import LocationAssets from '@/components/locations/LocationAssets.vue';
import LocationValueRow from '@/components/locations/LocationValueRow.vue';
import { useLocationInfo } from '@/composables/balances';
import { isSectionLoading } from '@/composables/common';
import { useAssetMovements } from '@/store/history/asset-movements';
import { useLedgerActions } from '@/store/history/ledger-actions';
import { useTrades } from '@/store/history/trades';
import { Section } from '@/types/status';
import { TradeLocationData } from '@/types/trades';

const props = defineProps({
  identifier: { required: true, type: String }
});

const { identifier } = toRefs(props);

const { getLocation } = useLocationInfo();

const tradeStore = useTrades();
const { updateTradesPayload } = tradeStore;
const { trades } = storeToRefs(tradeStore);

const assetMovementStore = useAssetMovements();
const { updateAssetMovementsPayload } = assetMovementStore;
const { assetMovements } = storeToRefs(assetMovementStore);

const ledgerActionStore = useLedgerActions();
const { updateLedgerActionsPayload } = ledgerActionStore;
const { ledgerActions } = storeToRefs(ledgerActionStore);

const location = computed<TradeLocationData>(() =>
  getLocation(get(identifier))
);

onBeforeMount(async () => {
  const payload = { location: get(identifier) };
  await Promise.allSettled([
    updateTradesPayload(payload),
    updateAssetMovementsPayload(payload),
    updateLedgerActionsPayload(payload)
  ]);
});

const showTrades = computed<boolean>(() => {
  return get(isSectionLoading(Section.TRADES)) || get(trades)?.data.length > 0;
});

const showAssetMovements = computed<boolean>(() => {
  return (
    get(isSectionLoading(Section.ASSET_MOVEMENT)) ||
    get(assetMovements)?.data.length > 0
  );
});

const showLedgerActions = computed<boolean>(() => {
  return (
    get(isSectionLoading(Section.LEDGER_ACTIONS)) ||
    get(ledgerActions)?.data.length > 0
  );
});
</script>
