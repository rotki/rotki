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
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import DefiProtocolDetails from '@/components/helper/DefiProtocolDetails.vue';

export interface Protocol {
  name: string;
  icon: string;
  identifier: DefiProtocol;
}

@Component({
  components: { DefiProtocolDetails }
})
export default class DefiProtocolSelector extends Vue {
  @Prop({ required: true })
  value!: DefiProtocol | null;
  @Prop({ required: false, type: Boolean, default: false })
  liabilities!: boolean;

  get protocols(): Protocol[] {
    if (this.liabilities) {
      return [...this.dual, ...this.borrowing];
    }
    return [...this.dual, ...this.lending];
  }

  private readonly dual: Protocol[] = [
    {
      identifier: DefiProtocol.AAVE,
      name: 'Aave',
      icon: require('@/assets/images/defi/aave.svg')
    },
    {
      identifier: DefiProtocol.COMPOUND,
      name: 'Compound',
      icon: require('@/assets/images/defi/compound.svg')
    }
  ];

  private readonly borrowing: Protocol[] = [
    {
      identifier: DefiProtocol.MAKERDAO_VAULTS,
      name: 'MakerDAO Vaults',
      icon: require('@/assets/images/defi/makerdao.svg')
    },
    {
      identifier: DefiProtocol.LIQUITY,
      name: 'Liquity',
      icon: require('@/assets/images/defi/liquity.svg')
    }
  ];

  private readonly lending: Protocol[] = [
    {
      identifier: DefiProtocol.MAKERDAO_DSR,
      name: 'MakerDAO DSR',
      icon: require('@/assets/images/defi/makerdao.svg')
    },
    {
      identifier: DefiProtocol.YEARN_VAULTS,
      name: 'yearn.finance',
      icon: require('@/assets/images/defi/yearn_vaults.svg')
    },
    {
      identifier: DefiProtocol.YEARN_VAULTS_V2,
      name: 'yearn.finance v2',
      icon: require('@/assets/images/defi/yearn_vaults.svg')
    }
  ];

  search: string = '';

  @Emit()
  input(_selectedProtocols: DefiProtocol | null) {}
}
</script>
