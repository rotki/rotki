<script setup lang="ts">
import { DefiProtocol, SUPPORTED_MODULES, isDefiProtocol } from '@/types/modules';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    modelValue?: DefiProtocol | null;
    liabilities?: boolean;
  }>(),
  {
    value: null,
    liabilities: false,
  },
);

const emit = defineEmits<{
  (e: 'update:model-value', protocol: DefiProtocol | null): void;
}>();

const model = useSimpleVModel(props, emit);

const dual = [DefiProtocol.AAVE, DefiProtocol.COMPOUND];
const borrowing = [DefiProtocol.MAKERDAO_VAULTS, DefiProtocol.LIQUITY];
const lending = [DefiProtocol.MAKERDAO_DSR, DefiProtocol.YEARN_VAULTS, DefiProtocol.YEARN_VAULTS_V2];

const { liabilities } = toRefs(props);
const search = ref<string>('');

const { t } = useI18n();

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
      v-model="model"
      v-model:search-input="search"
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
      {{ model ? t('defi_protocol_selector.filter_specific') : t('defi_protocol_selector.filter_all') }}
    </div>
  </RuiCard>
</template>
