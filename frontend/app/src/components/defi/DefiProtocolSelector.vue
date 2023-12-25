<script setup lang="ts">
import { Module, SUPPORTED_MODULES } from '@/types/modules';

const props = withDefaults(
  defineProps<{
    value?: Module | null;
    liabilities?: boolean;
  }>(),
  {
    value: null,
    liabilities: false
  }
);

const emit = defineEmits<{
  (e: 'input', protocol: Module | null): void;
}>();

const dual = [Module.AAVE, Module.COMPOUND];
const borrowing = [Module.MAKERDAO_VAULTS, Module.LIQUITY];
const lending = [Module.MAKERDAO_DSR, Module.YEARN, Module.YEARN_V2];

const { liabilities } = toRefs(props);
const search = ref<string>('');

const { t } = useI18n();

const input = (_selectedProtocol: Module | null) => {
  emit('input', _selectedProtocol);
};

const protocols = computed<Module[]>(() => {
  if (get(liabilities)) {
    return [...dual, ...borrowing];
  }
  return [...dual, ...lending];
});

const protocolsData = computed(() =>
  SUPPORTED_MODULES.filter(({ identifier }) =>
    get(protocols).includes(identifier)
  )
);
</script>

<template>
  <RuiCard>
    <VAutocomplete
      :value="value"
      :search-input.sync="search"
      :items="protocolsData"
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
        <DefiIcon v-bind="attrs" :item="item" />
      </template>
      <template #item="{ attrs, item }">
        <DefiIcon v-bind="attrs" :item="item" />
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
