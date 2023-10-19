<script setup lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';

interface Protocol {
  name: string;
  icon: string;
  identifier: DefiProtocol;
}

const props = withDefaults(
  defineProps<{
    value?: DefiProtocol | null;
    liabilities?: boolean;
  }>(),
  {
    value: null,
    liabilities: false
  }
);

const emit = defineEmits<{
  (e: 'input', protocol: DefiProtocol | null): void;
}>();

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
  <RuiCard>
    <VAutocomplete
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
        <DefiProtocolDetails v-bind="attrs" :item="item" />
      </template>
      <template #item="{ attrs, item }">
        <DefiProtocolDetails v-bind="attrs" :item="item" />
      </template>
    </VAutocomplete>
    <div class="p-2 text-body-2 text-rui-text-secondary">
      {{
        value
          ? t('defi_protocol_selector.filter_specific')
          : t('defi_protocol_selector.filter_all')
      }}
    </div>
  </RuiCard>
</template>
