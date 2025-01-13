<script setup lang="ts">
import { useTemplateRef } from 'vue';
import EthStakingValidators from '@/components/accounts/EthStakingValidators.vue';
import { Module } from '@/types/modules';
import EthStakingPageSettingMenu from '@/components/staking/eth/EthStakingPageSettingMenu.vue';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import AccountDialog from '@/components/accounts/management/AccountDialog.vue';
import EthStakingStatistic from '@/components/staking/eth/EthStakingStatistic.vue';
import { useModules } from '@/composables/session/modules';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';

const { t } = useI18n();

const module = Module.ETH2;

const tab = ref<number>(0);
const account = ref<AccountManageState>();

const { isModuleEnabled } = useModules();
const enabled = isModuleEnabled(module);

const tabItem = useTemplateRef<InstanceType<typeof EthStakingValidators | typeof EthStakingStatistic>>('tabItem');
</script>

<template>
  <div>
    <ModuleNotActive
      v-if="!enabled"
      :modules="[module]"
    />

    <TablePageLayout
      v-else
      :title="[t('navigation_menu.staking'), t('staking.eth2')]"
      child
    >
      <template #buttons>
        <div class="flex items-center gap-3">
          <ActiveModules :modules="[module]" />

          <RuiTooltip :open-delay="400">
            <template #activator>
              <RuiButton
                variant="outlined"
                color="primary"
                :loading="tabItem?.refreshing"
                @click="tabItem?.refresh()"
              >
                <template #prepend>
                  <RuiIcon name="lu-refresh-ccw" />
                </template>
                {{ t('common.refresh') }}
              </RuiButton>
            </template>
            {{ tab === 0
              ? t('eth2_page.refresh_validator')
              : t('premium_components.staking.refresh') }}
          </RuiTooltip>
          <EthStakingPageSettingMenu />
        </div>
      </template>

      <RuiTabs
        v-model="tab"
        color="primary"
        class="border-default border rounded bg-white dark:bg-rui-grey-900 flex max-w-min mx-auto"
      >
        <RuiTab>{{ t('eth2_page.tabs.validators') }}</RuiTab>
        <RuiTab>{{ t('eth2_page.tabs.statistic') }}</RuiTab>
      </RuiTabs>

      <RuiTabItems v-model="tab">
        <RuiTabItem class="pt-1.5">
          <AccountDialog
            v-model="account"
            @edit="account = $event"
          />
          <EthStakingValidators ref="tabItem" />
        </RuiTabItem>
        <RuiTabItem class="pt-1.5">
          <EthStakingStatistic ref="tabItem" />
        </RuiTabItem>
      </RuiTabItems>
    </TablePageLayout>
  </div>
</template>
