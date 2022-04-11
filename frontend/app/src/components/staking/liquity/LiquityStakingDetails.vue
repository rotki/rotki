<template>
  <div>
    <v-row align="center" no-gutters class="pt-2">
      <v-col cols="6">
        <blockchain-account-selector
          v-model="selectedAccount"
          :label="$t('liquity_staking_details.select_account')"
          :chains="['ETH']"
          dense
          outlined
          no-padding
          flat
          :usable-addresses="availableAddresses"
        />
      </v-col>
      <v-col />
      <v-col v-if="$slots.modules" cols="auto">
        <slot name="modules" />
      </v-col>
      <v-col cols="auto" class="pl-2">
        <refresh-button
          :tooltip="$t('liquity_staking_details.refresh_tooltip')"
          :loading="eventsLoading || loading"
          @refresh="refresh"
        />
      </v-col>
    </v-row>

    <v-row v-if="stakingList.length > 0" class="mt-8">
      <v-col v-for="stake in stakingList" :key="stake.asset">
        <liquity-stake :stake="stake" />
      </v-col>
    </v-row>

    <liquity-stake-events
      :events="stakingEventsList"
      :loading="eventsLoading"
      class="mt-8"
    />
  </div>
</template>

<script lang="ts">
import { AssetBalance } from '@rotki/common';
import { GeneralAccount } from '@rotki/common/lib/account';
import {
  LiquityStaking,
  LiquityStakingEvent,
  LiquityStakingEvents
} from '@rotki/common/lib/liquity';
import { computed, defineComponent, ref } from '@vue/composition-api';
import { get, toRefs } from '@vueuse/core';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import LiquityStake from '@/components/staking/liquity/LiquityStake.vue';
import { isSectionLoading, setupThemeCheck } from '@/composables/common';
import { LiquityStakeEvents } from '@/premium/premium';
import { Section } from '@/store/const';
import { useLiquityStore } from '@/store/defi/liquity';

export default defineComponent({
  name: 'LiquityStakingDetails',
  components: {
    LiquityStake,
    RefreshButton,
    LiquityStakeEvents
  },
  setup() {
    const selectedAccount = ref<GeneralAccount | null>(null);

    const liquityStore = useLiquityStore();
    const { staking, stakingEvents } = toRefs(liquityStore);
    const { fetchStaking, fetchStakingEvents } = liquityStore;

    const stakingList = computed(() => {
      const staked: Record<string, AssetBalance> = {};
      const stake = get(staking) as LiquityStaking;
      for (const address in stake) {
        const account = get(selectedAccount);
        if (account && account.address !== address) {
          continue;
        }
        const addressStake = stake[address];
        const asset = addressStake.asset;
        const assetStake = staked[asset];

        if (assetStake) {
          staked[asset] = {
            asset: asset,
            usdValue: assetStake.usdValue.plus(addressStake.usdValue),
            amount: assetStake.amount.plus(addressStake.amount)
          };
        } else {
          staked[asset] = addressStake;
        }
      }
      return Object.values(staked);
    });

    const stakingEventsList = computed(() => {
      const allEvents = get(stakingEvents) as LiquityStakingEvents;
      const events: LiquityStakingEvent[] = [];
      for (const address in allEvents) {
        const account = get(selectedAccount);
        if (account && account.address !== address) {
          continue;
        }
        events.push(...allEvents[address]);
      }
      return events;
    });

    const availableAddresses = computed(() => {
      return [...Object.keys(get(staking)), ...Object.keys(get(stakingEvents))];
    });

    const { isMobile } = setupThemeCheck();

    const refresh = async () => {
      await fetchStaking(true);
      await fetchStakingEvents(true);
    };

    return {
      selectedAccount,
      availableAddresses,
      stakingList,
      stakingEventsList,
      refresh,
      isMobile,
      loading: isSectionLoading(Section.DEFI_LIQUITY_STAKING),
      eventsLoading: isSectionLoading(Section.DEFI_LIQUITY_STAKING_EVENTS)
    };
  }
});
</script>
