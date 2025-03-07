<script setup lang="ts">
import DefiIcon from '@/components/defi/DefiIcon.vue';
import {
  type PurgeableModule,
  PurgeableOnlyModule,
  SUPPORTED_MODULES,
  type SupportedModule,
} from '@/types/modules';

type PurgeableModuleEntry = Omit<SupportedModule, 'identifier'> & { identifier: PurgeableModule };

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<string | undefined>({ required: true });

const props = withDefaults(defineProps<{
  items?: PurgeableModule[];
}>(), {
  items: () => [],
});

const modules = computed<PurgeableModuleEntry[]>(() => {
  const items = props.items;

  const modules: PurgeableModuleEntry[] = [...SUPPORTED_MODULES, {
    icon: './assets/images/protocols/cowswap.jpg',
    identifier: PurgeableOnlyModule.COWSWAP,
    name: 'Cowswap',
  }, {
    icon: './assets/images/protocols/gnosis_pay.png',
    identifier: PurgeableOnlyModule.GNOSIS_PAY,
    name: 'Gnosis Pay',
  }];

  return modules.filter(item => (items && items.length > 0 ? items.includes(item.identifier) : true));
});
</script>

<template>
  <RuiAutoComplete
    v-bind="$attrs"
    v-model="model"
    data-cy="defi-input"
    :options="modules"
    key-attr="identifier"
    text-attr="name"
    auto-select-first
    clearable
    variant="outlined"
    :item-height="52"
  >
    <template #selection="{ item }">
      <DefiIcon :item="item" />
    </template>
    <template #item="{ item }">
      <DefiIcon :item="item" />
    </template>
  </RuiAutoComplete>
</template>
