<template>
  <v-tooltip top open-delay="400">
    <template #activator="{ on }">
      <v-row align="center" no-gutters class="flex-nowrap" v-on="on">
        <v-col cols="auto">
          <v-avatar left size="28px">
            <asset-icon size="24px" :identifier="account.chain" />
          </v-avatar>
        </v-col>

        <v-col
          cols="auto"
          :class="{ 'blur-content': !shouldShowAmount }"
          class="text-no-wrap"
        >
          <div v-if="ensName">{{ ensName }}</div>
          <div v-else>({{ truncateAddress(address, 6) }})</div>
        </v-col>
      </v-row>
    </template>
    <div>
      {{ account.address }}
    </div>
  </v-tooltip>
</template>

<script setup lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { PropType } from 'vue';
import { truncateAddress } from '@/filters';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { useSessionSettingsStore } from '@/store/settings/session';
import { randomHex } from '@/utils/data';

const AssetIcon = defineAsyncComponent(
  () => import('@/components/helper/display/icons/AssetIcon.vue')
);

const props = defineProps({
  account: { required: true, type: Object as PropType<GeneralAccount> }
});

const { account } = toRefs(props);
const { scrambleData, shouldShowAmount } = storeToRefs(
  useSessionSettingsStore()
);

const { ethNameSelector } = useEthNamesStore();

const address = computed<string>(() => {
  if (!get(scrambleData)) {
    return get(account).address;
  }
  return randomHex();
});

const ensName = computed<string | null>(() => {
  if (!get(scrambleData)) {
    return get(ethNameSelector(get(account).address));
  }

  return null;
});
</script>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.75em);
}

.account-display {
  &__label {
    > span {
      display: inline-block;
      text-overflow: clip;
      padding-top: 6px;
      line-height: 20px;
      max-width: 180px;
    }
  }
}
</style>
