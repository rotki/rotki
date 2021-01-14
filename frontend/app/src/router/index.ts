/* istanbul ignore file */

import Vue from 'vue';
import Router from 'vue-router';
import { Routes } from '@/router/routes';

Vue.use(Router);

export default new Router({
  mode: 'history',
  base: '/',
  routes: [
    {
      path: '*',
      redirect: '/'
    },
    {
      path: '/dashboard',
      alias: '/',
      name: 'dashboard',
      component: () => import('../views/Dashboard.vue')
    },
    {
      path: '/statistics',
      name: 'statistics',
      component: () => import('../views/Statistics.vue')
    },
    {
      path: Routes.PROFIT_LOSS_REPORT,
      name: 'profit-loss-report',
      component: () => import('../views/ProfitLossReport.vue')
    },
    {
      path: '/history',
      component: () => import('../views/history/History.vue'),
      children: [
        {
          path: '',
          name: 'trades',
          redirect: 'trades',
          component: () => import('../views/history/TradeHistory.vue')
        },
        {
          path: 'trades',
          component: () => import('../views/history/TradeHistory.vue')
        },
        {
          path: 'deposits-withdrawals',
          component: () => import('../views/history/DepositsWithdrawals.vue')
        },
        {
          path: 'transactions',
          component: () => import('../views/history/Transactions.vue')
        },
        {
          path: Routes.HISTORY_LEDGER_ACTIONS,
          component: () => import('../views/history/LedgerActions.vue')
        }
      ]
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/settings/Settings.vue'),
      children: [
        {
          path: 'general',
          component: () => import('../views/settings/GeneralSettings.vue')
        },
        {
          path: 'accounting',
          component: () => import('../views/settings/AccountingSettings.vue')
        },
        {
          path: 'data-security',
          component: () => import('../views/settings/UserSecuritySettings.vue')
        },
        {
          path: 'defi',
          component: () => import('../views/settings/DefiSettings.vue')
        }
      ]
    },
    {
      path: '/settings/general',
      name: 'general-settings',
      component: () => import('../views/settings/Settings.vue')
    },
    {
      path: '/settings/api-keys',
      name: 'api-keys',
      component: () => import('../views/settings/ApiKeys.vue'),
      children: [
        {
          path: 'rotki-premium',
          component: () => import('../components/settings/PremiumSettings.vue')
        },
        {
          path: 'exchanges',
          component: () =>
            import('../components/settings/api-keys/ExchangeSettings.vue')
        },
        {
          path: 'external-services',
          component: () =>
            import('../components/settings/api-keys/ExternalServices.vue')
        }
      ]
    },
    {
      path: '/import',
      name: 'import',
      component: () => import('../views/ImportData.vue')
    },
    {
      path: '/accounts-balances',
      component: () => import('../views/AccountsBalances.vue'),
      children: [
        {
          path: '',
          name: 'accounts-balances',
          redirect: 'blockchain-balances'
        },
        {
          path: 'blockchain-balances',
          component: () =>
            import('../components/accounts/BlockchainBalances.vue')
        },
        {
          path: 'exchange-balances/',
          component: () => import('../components/accounts/ExchangeBalances.vue')
        },
        {
          path: 'exchange-balances/:exchange',
          component: () =>
            import('../components/accounts/ExchangeBalances.vue'),
          props: true
        },
        {
          path: 'manual-balances',
          component: () => import('../components/accounts/ManualBalances.vue')
        }
      ]
    },
    {
      path: Routes.DEFI,
      component: () => import('../views/defi/DecentralizedFinance.vue'),
      children: [
        {
          path: '',
          redirect: Routes.DEFI_OVERVIEW
        },
        {
          path: Routes.DEFI_OVERVIEW,
          component: () => import('../views/defi/DecentralizedOverview.vue')
        },
        {
          path: Routes.DEFI_DEPOSITS,
          component: () => import('../views/defi/DecentralizedDeposits.vue'),
          children: [
            {
              path: '',
              redirect: Routes.DEFI_DEPOSITS_PROTOCOLS
            },
            {
              path: Routes.DEFI_DEPOSITS_PROTOCOLS,
              component: () => import('../views/defi/deposits/Protocols.vue')
            },
            {
              path: Routes.DEFI_DEPOSITS_LIQUIDITY,
              component: () => import('../views/defi/deposits/Liquidity.vue')
            }
          ]
        },
        {
          path: Routes.DEFI_LIABILITIES,
          name: 'defi-liabilities',
          component: () => import('../views/defi/DecentralizedBorrowing.vue')
        },
        {
          path: Routes.DEFI_DEX_TRADES,
          component: () => import('../views/defi/DexTrades.vue')
        },
        {
          path: Routes.DEFI_AIRDROPS,
          component: () => import('../views/defi/Airdrops.vue')
        }
      ]
    },
    {
      path: Routes.STAKING,
      component: () => import('../views/Staking.vue'),
      children: [
        {
          path: '',
          redirect: Routes.STAKING_ETH2
        },
        {
          path: Routes.STAKING_ETH2,
          component: () => import('../views/staking/Eth2Page.vue')
        },
        {
          path: Routes.STAKING_ADEX,
          component: () => import('../views/staking/AdexPage.vue')
        }
      ]
    },
    ...(process.env.NODE_ENV === 'development'
      ? [
          {
            path: '/playground',
            name: 'playground',
            component: () => import('../views/dev/Playground.vue')
          }
        ]
      : [])
  ]
});
