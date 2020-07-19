<template>
  <v-card>
    <div class="mx-4 pt-2">
      <v-autocomplete
        v-model="selectedProtocols"
        :search-input.sync="search"
        :multiple="multiple"
        :items="supportedProtocols"
        return-object
        hide-details
        hide-selected
        hide-no-data
        clearable
        chips
        :open-on-clear="false"
        label="Filter protocol(s)"
        item-text="name"
        item-value="name"
        class="defi-protocol-selector"
      >
        <template #selection="data">
          <span>
            <v-img
              width="55px"
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
              width="55px"
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
      Showing results across
      {{ selectedProtocols.length > 0 ? selectedAccountsArray.length : 'all' }}
      protocols.
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

type SelectedAccountsParams = Protocol[] | Protocol | null;

@Component({})
export default class DefiProtocolSelector extends Vue {
  protocolSelection: Protocol[] = [];
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

  @Prop({ required: false, type: Boolean, default: false })
  multiple!: boolean;
  search: string = '';

  private unselectAll() {
    for (let i = 0; i < this.protocolSelection.length; i++) {
      this.protocolSelection.pop();
    }
  }

  set selectedProtocols(value: SelectedAccountsParams) {
    if (!value) {
      this.unselectAll();
    } else if (Array.isArray(value)) {
      this.protocolSelection.push(...value);
    } else {
      if (!this.multiple) {
        this.unselectAll();
      }
      this.protocolSelection.push(value);
    }
    this.selectionChanged(this.protocolSelection);
    if (this.search) {
      this.search = '';
    }
  }

  get selectedProtocols(): SelectedAccountsParams {
    if (this.protocolSelection.length === 0) {
      return [];
    } else if (this.protocolSelection.length === 1) {
      const [first] = this.protocolSelection;
      return first;
    }
    return this.protocolSelection;
  }

  @Emit()
  selectionChanged(_selectedProtocols: Protocol[]) {}
}
</script>

<style scoped lang="scss"></style>
