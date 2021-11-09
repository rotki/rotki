<template>
  <fragment>
    <v-row>
      <v-col>
        <blockchain-account-selector
          v-model="selectedAccount"
          :label="$t('liquity_staking_details.select_account')"
          :chains="['ETH']"
          dense
          outlined
          no-padding
          flat
          :usable-addresses="availableAddresses"
          :max-width="isMobile ? '100%' : '250px'"
        />
      </v-col>
      <v-col v-if="$slots.modules" cols="auto">
        <slot name="modules" />
      </v-col>
      <v-col cols="auto">
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
  </fragment>
</template>

<script lang="ts">
import { AssetBalance } from '@rotki/common';
import { GeneralAccount } from '@rotki/common/lib/account';
import { LiquityStakingEvent } from '@rotki/common/lib/liquity';
import { computed, defineComponent, ref } from '@vue/composition-api';
import Fragment from '@/components/helper/Fragment';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import LiquityStake from '@/components/staking/liquity/LiquityStake.vue';
import { isSectionLoading, setupThemeCheck } from '@/composables/common';
import { LiquityStakeEvents } from '@/premium/premium';
import { Section } from '@/store/const';
import { RotkehlchenState } from '@/store/types';
import { useStore } from '@/store/utils';

export default defineComponent({
  name: 'LiquityStakingDetails',
  components: {
    LiquityStake,
    RefreshButton,
    Fragment,
    LiquityStakeEvents
  },
  setup() {
    const selectedAccount = ref<GeneralAccount | null>(null);
    const store = useStore();
    const state: RotkehlchenState = store.state;

    const stakingList = computed(() => {
      const { staking } = state.defi!!.liquity!!;
      const staked: Record<string, AssetBalance> = {};
      for (const address in staking) {
        const account = selectedAccount.value;
        if (account && account.address !== address) {
          continue;
        }
        const addressStake = staking[address];
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
      const { stakingEvents } = state.defi!!.liquity!!;
      const events: LiquityStakingEvent[] = [];
      for (const address in stakingEvents) {
        const account = selectedAccount.value;
        if (account && account.address !== address) {
          continue;
        }
        events.push(...stakingEvents[address]);
      }
      return events;
    });

    const availableAddresses = computed(() => {
      const { staking, stakingEvents } = state.defi!!.liquity!!;
      return [...Object.keys(staking), ...Object.keys(stakingEvents)];
    });

    const { isMobile } = setupThemeCheck();

    const refresh = async () => {
      await store.dispatch('defi/liquity/fetchStaking', true);
      await store.dispatch('defi/liquity/fetchStakingEvents', true);
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
