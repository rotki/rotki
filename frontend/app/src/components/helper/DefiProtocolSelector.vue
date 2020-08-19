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
        <template #selection="data">
          <span>
            <v-img
              width="26px"
              contain
              position="left"
              max-height="24px"
              :src="data.item.icon"
            />
          </span>
        </template>
        <template #item="data">
          <span v-bind="data.attrs">
            <v-img
              width="26px"
              contain
              position="left"
              max-height="24px"
              :src="data.item.icon"
            />
          </span>
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
import { SupportedDefiProtocols } from '@/services/defi/types';

export interface Protocol {
  name: string;
  icon: string;
  identifier: SupportedDefiProtocols;
}

@Component({})
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
    }
  ];

  search: string = '';

  @Emit()
  input(_selectedProtocols: SupportedDefiProtocols | null) {}
}
</script>

<style scoped lang="scss"></style>
