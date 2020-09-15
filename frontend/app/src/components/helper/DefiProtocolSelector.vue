<template>
  <v-card>
    <div class="mx-4 pt-2">
      <v-autocomplete
        :value="value"
        :search-input.sync="search"
        :items="supportedProtocols"
        hide-details
        hide-selected
        hide-no-data
        clearable
        chips
        :open-on-clear="false"
        label="Filter protocol(s)"
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
        value ? 'Showing results for selected protocol' : 'Showing all results'
      }}
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator';
import DefiProtocolDetails from '@/components/helper/DefiProtocolDetails.vue';
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

  supportedProtocols: Protocol[] = [
    {
      identifier: 'aave',
      name: 'Aave',
      icon: require('@/assets/images/defi/aave.svg')
    },
    {
      identifier: 'makerdao',
      name: 'MakerDAO',
      icon: require('@/assets/images/defi/makerdao.svg')
    },
    {
      identifier: 'compound',
      name: 'Compound',
      icon: require('@/assets/images/defi/compound.svg')
    }
  ];

  search: string = '';

  @Emit()
  input(_selectedProtocols: SupportedDefiProtocols | null) {}
}
</script>
