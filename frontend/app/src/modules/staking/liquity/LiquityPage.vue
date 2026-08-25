<script setup lang="ts">
import ActiveModules from '@/modules/settings/modules/ActiveModules.vue';
import ModuleNotActive from '@/modules/settings/modules/ModuleNotActive.vue';
import LiquityStakingDetails from '@/modules/staking/liquity/LiquityStakingDetails.vue';
import LiquityStakingPagePlaceholder from '@/modules/staking/liquity/LiquityStakingPagePlaceholder.vue';
import { LIQUITY_MODULES, useLiquityPage } from '@/modules/staking/liquity/use-liquity-page';

const { t } = useI18n({ useScope: 'global' });

const { fetch, moduleEnabled, premium } = useLiquityPage();
</script>

<template>
  <div>
    <LiquityStakingPagePlaceholder
      v-if="!premium"
      :text="t('liquity_page.no_premium')"
      data-testid="no-premium"
    />
    <ModuleNotActive
      v-else-if="!moduleEnabled"
      :modules="LIQUITY_MODULES"
      data-testid="module-not-active"
    />
    <LiquityStakingDetails
      v-else
      data-testid="staking-details"
      @refresh="fetch($event)"
    >
      <template #modules>
        <ActiveModules :modules="LIQUITY_MODULES" />
      </template>
    </LiquityStakingDetails>
  </div>
</template>
