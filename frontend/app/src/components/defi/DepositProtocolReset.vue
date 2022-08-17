<template>
  <confirmable-reset
    v-if="premium"
    :loading="loading"
    :tooltip="tc('lending.reset_tooltip')"
    :disabled="resetSelection.length === 0"
    @reset="reset()"
  >
    {{ $t('lending.reset_confirm') }}
    <div />
    <v-row>
      <v-col class="text-center font-weight-medium">
        {{ $t('lending.reset.protocol_selection') }}
      </v-col>
    </v-row>
    <v-row align="center" justify="center">
      <v-col cols="auto">
        <v-btn-toggle v-model="resetSelection" multiple>
          <v-btn icon :value="AAVE">
            <defi-protocol-icon mode="icon" :protocol="AAVE" />
          </v-btn>
          <v-btn icon :value="YEARN_VAULTS">
            <defi-protocol-icon mode="icon" :protocol="YEARN_VAULTS" />
          </v-btn>
          <v-btn icon :value="YEARN_VAULTS_V2">
            <defi-protocol-icon mode="icon" :protocol="YEARN_VAULTS_V2" />
          </v-btn>
        </v-btn-toggle>
      </v-col>
    </v-row>
  </confirmable-reset>
</template>
<script lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { defineComponent, ref } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { useI18n } from 'vue-i18n-composable';
import ConfirmableReset from '@/components/helper/ConfirmableReset.vue';
import { getPremium } from '@/composables/session';

export default defineComponent({
  name: 'DepositProtocolReset',
  components: { ConfirmableReset },
  props: {
    loading: {
      required: true,
      type: Boolean
    }
  },
  emits: ['reset'],
  setup(_, { emit }) {
    const resetSelection = ref<DefiProtocol[]>([]);
    const premium = getPremium();
    const AAVE = DefiProtocol.AAVE;
    const YEARN_VAULTS = DefiProtocol.YEARN_VAULTS;
    const YEARN_VAULTS_V2 = DefiProtocol.YEARN_VAULTS_V2;

    const { tc } = useI18n();

    const reset = () => {
      emit('reset', get(resetSelection));
    };

    return {
      resetSelection,
      premium,
      AAVE,
      YEARN_VAULTS,
      YEARN_VAULTS_V2,
      reset,
      tc
    };
  }
});
</script>
