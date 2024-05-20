<script setup lang="ts">
import {
  DefiProtocol,
  SUPPORTED_MODULES,
  isDefiProtocol,
} from '@/types/modules';

const props = withDefaults(
  defineProps<{
    value?: DefiProtocol | null;
    liabilities?: boolean;
  }>(),
  {
    value: null,
    liabilities: false,
  },
);

const emit = defineEmits<{
  (e: 'input', protocol: DefiProtocol | null): void;
}>();

const dual = [DefiProtocol.AAVE, DefiProtocol.COMPOUND];
const borrowing = [DefiProtocol.MAKERDAO_VAULTS, DefiProtocol.LIQUITY];
const lending = [
  DefiProtocol.MAKERDAO_DSR,
  DefiProtocol.YEARN_VAULTS,
  DefiProtocol.YEARN_VAULTS_V2,
];

const { liabilities } = toRefs(props);
const search = ref<string>('');

const { t } = useI18n();

function input(_selectedProtocol: DefiProtocol | null) {
  emit('input', _selectedProtocol);
}

const protocols = computed<DefiProtocol[]>(() => {
  if (get(liabilities))
    return [...dual, ...borrowing];

  return [...dual, ...lending];
});

const protocolsData = computed(() =>
  SUPPORTED_MODULES.filter(({ identifier }) => {
    if (!isDefiProtocol(identifier))
      return false;

    return get(protocols).includes(identifier);
  }),
);
</script>

<template>
  <RuiCard>
    <RuiAutoComplete
      :value="value"
      :search-input.sync="search"
      :options="protocolsData"
      hide-details
      hide-selected
      hide-no-data
      clearable
      dense
      auto-select-first
      :item-height="44"
      variant="outlined"
      :label="t('defi_protocol_selector.label')"
      text-attr="name"
      key-attr="identifier"
      class="defi-protocol-selector"
      @input="input($event)"
    >
      <template #selection="{ item }">
        <DefiIcon
          :item="item"
          size="1.125rem"
        />
      </template>
      <template #item="{ item }">
        <DefiIcon
          class="py-1"
          :item="item"
        />
      </template>
    </RuiAutoComplete>
    <div class="p-2 text-body-2 text-rui-text-secondary">
      {{
        value
          ? t('defi_protocol_selector.filter_specific')
          : t('defi_protocol_selector.filter_all')
      }}
    </div>
  </RuiCard>
</template>
