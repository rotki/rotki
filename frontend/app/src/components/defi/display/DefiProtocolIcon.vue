<template>
  <div
    class="d-flex flex-row align-center"
    :class="mode === 'icon' ? 'justify-center' : null"
  >
    <v-tooltip top :disabled="mode !== 'icon'" open-delay="300ms">
      <template #activator="{ on, attrs }">
        <v-img
          v-if="mode === 'icon' || mode === 'both'"
          contain
          v-bind="attrs"
          max-width="24px"
          max-height="24"
          :class="{
            'mr-2': mode !== 'icon',
            [$style.icon]: true
          }"
          :src="require(`@/assets/images/defi/${icon}.svg`)"
          v-on="on"
        />
        <span
          v-if="mode === 'label' || mode === 'both'"
          class="text--secondary"
          :class="$style.label"
        >
          {{ capitalize(name) }}
        </span>
      </template>
      <span>
        {{ capitalize(name) }}
      </span>
    </v-tooltip>
  </div>
</template>
<script lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { computed, defineComponent, PropType } from '@vue/composition-api';
import { capitalize } from '@/filters';

export default defineComponent({
  name: 'DefiProtocolIcon',
  props: {
    protocol: {
      required: true,
      type: String as PropType<DefiProtocol>
    },
    mode: {
      required: false,
      default: 'both',
      type: String as PropType<'icon' | 'label' | 'both'>
    }
  },
  setup() {
    const icon = computed(({ protocol }) => {
      if (protocol.endsWith('_v2')) {
        return protocol.replace('_v2', '');
      }
      if (protocol.startsWith('makerdao')) {
        return 'makerdao';
      }
      return protocol;
    });

    const name = computed(({ protocol }) => {
      if (protocol === DefiProtocol.MAKERDAO_DSR) {
        return 'MakerDAO DSR';
      } else if (protocol === DefiProtocol.MAKERDAO_VAULTS) {
        return 'MakerDAO Vaults';
      } else if (protocol === DefiProtocol.YEARN_VAULTS) {
        return 'yearn.finance Vaults';
      } else if (protocol === DefiProtocol.YEARN_VAULTS_V2) {
        return 'yearn.finance Vaults v2';
      }
      return protocol;
    });
    return {
      icon,
      name,
      capitalize: capitalize
    };
  }
});
</script>

<style lang="scss" module>
.icon {
  max-width: 30px;
}

.label {
  font-size: 12px;
}
</style>
