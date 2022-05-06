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
          class="font-weight-bold mr-1 account-display__label text-no-wrap"
        >
          <span class="text-truncate">
            {{ account.label }}
          </span>
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

<script lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { setupDisplayData } from '@/composables/session';
import { truncateAddress } from '@/filters';
import { useEnsNamesStore } from '@/store/balances';
import { randomHex } from '@/utils/data';

export default defineComponent({
  name: 'AccountDisplay',
  components: { AssetIcon },
  props: {
    account: { required: true, type: Object as PropType<GeneralAccount> }
  },
  setup(props) {
    const { account } = toRefs(props);
    const { scrambleData, shouldShowAmount } = setupDisplayData();

    const { ensNameSelector } = useEnsNamesStore();

    const address = computed<string>(() => {
      if (!get(scrambleData)) {
        return get(account).address;
      }
      return randomHex();
    });

    const ensName = computed<string | null>(() => {
      if (!get(scrambleData)) {
        return get(ensNameSelector(get(account).address));
      }

      return null;
    });

    return {
      ensName,
      address,
      truncateAddress,
      shouldShowAmount
    };
  }
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
