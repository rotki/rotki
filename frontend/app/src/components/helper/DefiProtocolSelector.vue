<script setup lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { type PropType } from 'vue';

interface Protocol {
  name: string;
  icon: string;
  identifier: DefiProtocol;
}

const dual: Protocol[] = [
  {
    identifier: DefiProtocol.AAVE,
    name: 'Aave',
    icon: './assets/images/protocols/aave.svg'
  },
  {
    identifier: DefiProtocol.COMPOUND,
    name: 'Compound',
    icon: './assets/images/protocols/compound.svg'
  }
];

const borrowing: Protocol[] = [
  {
    identifier: DefiProtocol.MAKERDAO_VAULTS,
    name: 'MakerDAO Vaults',
    icon: './assets/images/protocols/makerdao.svg'
  },
  {
    identifier: DefiProtocol.LIQUITY,
    name: 'Liquity',
    icon: './assets/images/protocols/liquity.svg'
  }
];

const lending: Protocol[] = [
  {
    identifier: DefiProtocol.MAKERDAO_DSR,
    name: 'MakerDAO DSR',
    icon: './assets/images/protocols/makerdao.svg'
  },
  {
    identifier: DefiProtocol.YEARN_VAULTS,
    name: 'yearn.finance',
    icon: './assets/images/protocols/yearn_vaults.svg'
  },
  {
    identifier: DefiProtocol.YEARN_VAULTS_V2,
    name: 'yearn.finance v2',
    icon: './assets/images/protocols/yearn_vaults.svg'
  }
];

const props = defineProps({
  value: {
    required: false,
    type: String as PropType<DefiProtocol | null>,
    default: null
  },
  liabilities: { required: false, type: Boolean, default: false }
});

const emit = defineEmits<{
  (e: 'input', protocol: DefiProtocol | null): void;
}>();

const { liabilities } = toRefs(props);
const search = ref<string>('');

const { t } = useI18n();

const input = (_selectedProtocol: DefiProtocol | null) => {
  emit('input', _selectedProtocol);
};

const protocols = computed<Protocol[]>(() => {
  if (get(liabilities)) {
    return [...dual, ...borrowing];
  }
  return [...dual, ...lending];
});
</script>

<template>
  <v-card>
    <div class="mx-4 pt-4">
      <v-autocomplete
        :value="value"
        :search-input.sync="search"
        :items="protocols"
        hide-details
        hide-selected
        hide-no-data
        clearable
        chips
        dense
        outlined
        :open-on-clear="false"
        :label="t('defi_protocol_selector.label')"
        item-text="name"
        item-value="identifier"
        class="defi-protocol-selector"
        @input="input($event)"
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
          ? t('defi_protocol_selector.filter_specific')
          : t('defi_protocol_selector.filter_all')
      }}
    </v-card-text>
  </v-card>
</template>
