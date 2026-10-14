<script setup lang="ts">
import { provideHistoryEventsSection } from '@/modules/history/events/use-history-events-section';
import ModuleNotActive from '@/modules/settings/modules/ModuleNotActive.vue';
import ModuleSettingsMenu from '@/modules/settings/modules/ModuleSettingsMenu.vue';
import LiquityStakingDetails from '@/modules/staking/liquity/LiquityStakingDetails.vue';
import LiquityStakingPagePlaceholder from '@/modules/staking/liquity/LiquityStakingPagePlaceholder.vue';
import { LIQUITY_MODULES, useLiquityPage } from '@/modules/staking/liquity/use-liquity-page';
import { useStakingHistorySync } from '@/modules/staking/use-staking-history-sync';

const { t } = useI18n({ useScope: 'global' });

const { fetch, moduleEnabled, premium } = useLiquityPage();

// The page's Refresh covers the staking events too, so the events section drops its own.
const { reload: reloadEvents } = provideHistoryEventsSection();
const { chainName, syncHistory, syncingHistory } = useStakingHistorySync(reloadEvents);

async function refresh(): Promise<void> {
  await fetch(true);
  reloadEvents();
}
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
      :syncing-history="syncingHistory"
      :chain-name="chainName"
      data-testid="staking-details"
      @refresh="refresh()"
      @sync-history="syncHistory()"
    >
      <template #modules>
        <ModuleSettingsMenu :modules="LIQUITY_MODULES" />
      </template>
    </LiquityStakingDetails>
  </div>
</template>
