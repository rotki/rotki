<template>
  <v-card>
    <div class="mx-4 pt-2">
      <v-autocomplete
        :value="value"
        :search-input.sync="search"
        :items="protocols"
        hide-details
        hide-selected
        hide-no-data
        clearable
        chips
        :open-on-clear="false"
        :label="$t('defi_protocol_selector.label')"
        item-text="name"
        item-value="identifier"
        class="defi-protocol-selector"
        @input="input"
      >
        <template #selection="{ attrs, item }">
          <defi-protocol-details v-bind="attrs" :item="item" />
        </template>
        <template #item="{ attrs, item }">
          <defi-protocol-details v-bind="attrs" :item="item" />
        </template>
      </v-autocomplete>
    </div>
    <v-card-text>
      {{
        value
          ? $t('defi_protocol_selector.filter_specific')
          : $t('defi_protocol_selector.filter_all')
      }}
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import DefiProtocolDetails from '@/components/helper/DefiProtocolDetails.vue';

export interface Protocol {
  name: string;
  icon: string;
  identifier: DefiProtocol;
}

const dual: Protocol[] = [
  {
    identifier: DefiProtocol.AAVE,
    name: 'Aave',
    icon: '/assets/images/defi/aave.svg'
  },
  {
    identifier: DefiProtocol.COMPOUND,
    name: 'Compound',
    icon: '/assets/images/defi/compound.svg'
  }
];

const borrowing: Protocol[] = [
  {
    identifier: DefiProtocol.MAKERDAO_VAULTS,
    name: 'MakerDAO Vaults',
    icon: '/assets/images/defi/makerdao.svg'
  },
  {
    identifier: DefiProtocol.LIQUITY,
    name: 'Liquity',
    icon: '/assets/images/defi/liquity.svg'
  }
];

const lending: Protocol[] = [
  {
    identifier: DefiProtocol.MAKERDAO_DSR,
    name: 'MakerDAO DSR',
    icon: '/assets/images/defi/makerdao.svg'
  },
  {
    identifier: DefiProtocol.YEARN_VAULTS,
    name: 'yearn.finance',
    icon: '/assets/images/defi/yearn_vaults.svg'
  },
  {
    identifier: DefiProtocol.YEARN_VAULTS_V2,
    name: 'yearn.finance v2',
    icon: '/assets/images/defi/yearn_vaults.svg'
  }
];

export default defineComponent({
  name: 'DefiProtocolSelector',
  components: { DefiProtocolDetails },
  props: {
    value: {
      required: false,
      type: String as PropType<DefiProtocol>,
      default: ''
    },
    liabilities: { required: false, type: Boolean, default: false }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { liabilities } = toRefs(props);
    const search = ref<string>('');

    const input = (_selectedProtocol: DefiProtocol | null) => {
      emit('input', _selectedProtocol);
    };

    const protocols = computed<Protocol[]>(() => {
      if (get(liabilities)) {
        return [...dual, ...borrowing];
      }
      return [...dual, ...lending];
    });

    return {
      search,
      input,
      protocols
    };
  }
});
</script>
