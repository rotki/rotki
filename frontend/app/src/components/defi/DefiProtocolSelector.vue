<script setup lang="ts">
import { DefiProtocol, SUPPORTED_MODULES, type SupportedModule, isDefiProtocol } from '@/types/modules';
import DefiIcon from '@/components/defi/DefiIcon.vue';

type SupportedProtocol = Omit<SupportedModule, 'identifier'> & { identifier: DefiProtocol };

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<DefiProtocol | undefined>({ required: true });

const props = withDefaults(defineProps<{
  liabilities?: boolean;
}>(), {
  liabilities: false,
});

const dual = [DefiProtocol.AAVE, DefiProtocol.COMPOUND] as const;
const borrowing = [DefiProtocol.MAKERDAO_VAULTS, DefiProtocol.LIQUITY] as const;
const lending = [DefiProtocol.MAKERDAO_DSR, DefiProtocol.YEARN_VAULTS, DefiProtocol.YEARN_VAULTS_V2] as const;

const { liabilities } = toRefs(props);
const search = ref<string>('');

const { t } = useI18n();

const protocols = computed<DefiProtocol[]>(() => get(liabilities) ? [...dual, ...borrowing] : [...dual, ...lending]);

const protocolsData = computed<SupportedProtocol[]>(() => {
  const data: SupportedProtocol[] = [];
  for (const module of SUPPORTED_MODULES) {
    const identifier = module.identifier;
    if (isDefiProtocol(identifier) && get(protocols).includes(identifier)) {
      data.push({
        ...module,
        identifier,
      });
    }
  }

  return data;
},

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
