<script setup lang="ts">
import type {
  EthStakingCombinedFilter,
  EthStakingFilter,
  EthStakingFilterType,
} from '@rotki/common/lib/staking/eth2';

const props = defineProps<{
  modelValue: EthStakingFilter;
  filter: EthStakingCombinedFilter | undefined;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: EthStakingFilter): void;
  (e: 'update:filter', value?: EthStakingCombinedFilter): void;
}>();

const filterType = ref<EthStakingFilterType>('validator');
const filterModel = useVModel(props, 'filter', emit);

const model = useSimpleVModel(props, emit);

watch(filterType, type =>
  emit('update:model-value', type === 'validator' ? { validators: [] } : { accounts: [] }));

const { t } = useI18n();
</script>

<template>
  <div class="flex flex-col md:flex-row md:items-center gap-4 md:gap-12">
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
      tooltip-class="max-w-[12rem]"
    >
      <template #activator>
        <RuiButtonGroup
          v-model="filterType"
          required
          variant="outlined"
          color="primary"
        >
          <RuiButton
            value="validator"
            class="!py-2"
          >
            {{ t('eth2_page.toggle.key') }}
          </RuiButton>
          <RuiButton
            value="address"
            class="!py-2"
          >
            {{ t('eth2_page.toggle.withdrawal') }}
          </RuiButton>
        </RuiButtonGroup>
      </template>
      <span>{{ t('eth2_page.toggle.hint') }}</span>
    </RuiTooltip>
    <div class="grid sm:grid-cols-2 flex-1 gap-4">
      <Eth2ValidatorFilter
        v-model="model"
        :filter-type="filterType"
      />
      <EthValidatorCombinedFilter v-model:filter="filterModel" />
    </div>
  </div>
</template>
