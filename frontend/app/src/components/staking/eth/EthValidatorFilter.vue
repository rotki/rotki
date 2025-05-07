<script setup lang="ts">
import type { EthStakingCombinedFilter, EthStakingFilter, EthStakingFilterType } from '@rotki/common';
import Eth2ValidatorFilter from '@/components/helper/filter/Eth2ValidatorFilter.vue';
import EthValidatorCombinedFilter from '@/components/staking/eth/EthValidatorCombinedFilter.vue';

const filterModel = defineModel<EthStakingCombinedFilter | undefined>('filter', { required: true });
const model = defineModel<EthStakingFilter>({ required: true });

const filterType = ref<EthStakingFilterType>('validator');

watch(filterType, type => set(model, type === 'validator' ? { validators: [] } : { accounts: [] }));

const { t } = useI18n({ useScope: 'global' });

const disableStatus = computed<boolean>(() => {
  const modelFilter = get(model);
  return 'validators' in modelFilter && modelFilter.validators.length > 0;
});
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
            model-value="validator"
            class="!py-2"
          >
            {{ t('eth2_page.toggle.key') }}
          </RuiButton>
          <RuiButton
            model-value="address"
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
      <EthValidatorCombinedFilter
        v-model:filter="filterModel"
        :disable-status="disableStatus"
      />
    </div>
  </div>
</template>
