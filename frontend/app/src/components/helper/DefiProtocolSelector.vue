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
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import DefiProtocolDetails from '@/components/helper/DefiProtocolDetails.vue';
import {
  DEFI_AAVE,
  DEFI_COMPOUND,
  DEFI_MAKERDAO,
  DEFI_YEARN_VAULTS,
  DEFI_YEARN_VAULTS_V2
} from '@/services/defi/consts';
import { SupportedDefiProtocols } from '@/services/defi/types';

export interface Protocol {
  name: string;
  icon: string;
  identifier: SupportedDefiProtocols;
}

@Component({
  components: { DefiProtocolDetails }
})
export default class DefiProtocolSelector extends Vue {
  @Prop({ required: true })
  value!: SupportedDefiProtocols | null;
  @Prop({ required: false, type: Boolean, default: false })
  liabilities!: boolean;

  get protocols(): Protocol[] {
    if (this.liabilities) {
      return this.dual;
    }
    return [...this.dual, ...this.lending];
  }

  private readonly dual: Protocol[] = [
    {
      identifier: DEFI_AAVE,
      name: 'Aave',
      icon: require('@/assets/images/defi/aave.svg')
    },
    {
      identifier: DEFI_MAKERDAO,
      name: 'MakerDAO',
      icon: require('@/assets/images/defi/makerdao.svg')
    },
    {
      identifier: DEFI_COMPOUND,
      name: 'Compound',
      icon: require('@/assets/images/defi/compound.svg')
    }
  ];

  private readonly lending: Protocol[] = [
    {
      identifier: DEFI_YEARN_VAULTS,
      name: 'yearn.finance',
      icon: require('@/assets/images/defi/yearn_vaults.svg')
    },
    {
      identifier: DEFI_YEARN_VAULTS_V2,
      name: 'yearn.finance v2',
      icon: require('@/assets/images/defi/yearn_vaults.svg')
    }
  ];

  search: string = '';

  @Emit()
  input(_selectedProtocols: SupportedDefiProtocols | null) {}
}
</script>
