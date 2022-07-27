/* istanbul ignore file */

import Vue from 'vue';
import Router from 'vue-router';
import { Routes } from '@/router/routes';

Vue.use(Router);

const base = import.meta.env.VITE_PUBLIC_PATH ? window.location.pathname : '/';
const isDocker = import.meta.env.VITE_DOCKER;

export default new Router({
  mode: isDocker ? 'hash' : 'history',
  base,
  scrollBehavior: (to, from, savedPosition) => {
    if (to.hash) {
      setTimeout(() => {
        const element = document.getElementById(to.hash.replace(/#/, ''));
        if (element && element.scrollIntoView) {
          element.scrollIntoView({ block: 'end', behavior: 'smooth' });
        }
      }, 500);

      return { selector: to.hash };
    } else if (savedPosition) {
      return savedPosition;
    }
    return { x: 0, y: 0 };
  },
  routes: [
    {
      path: '*',
      redirect: Routes.ROOT.route
    },
    {
      path: Routes.DASHBOARD.route,
      alias: Routes.ROOT.route,
      name: 'dashboard',
      component: async () => import('../views/Dashboard.vue')
    },
    {
      path: Routes.ACCOUNTS_BALANCES.route,
      component: async () => import('../views/AccountsBalances.vue'),
      children: [
        {
          path: '',
          name: 'accounts-balances',
          redirect: Routes.ACCOUNTS_BALANCES_BLOCKCHAIN.route
        },
        {
          path: Routes.ACCOUNTS_BALANCES_BLOCKCHAIN.route,
          component: () =>
            import('../components/accounts/BlockchainBalances.vue')
        },
        {
          path: Routes.ACCOUNTS_BALANCES_EXCHANGE.route,
          component: () =>
            import('../components/accounts/exchanges/ExchangeBalances.vue')
        },
        {
          path: `${Routes.ACCOUNTS_BALANCES_EXCHANGE.route}/:exchange`,
          component: () =>
            import('../components/accounts/exchanges/ExchangeBalances.vue'),
          props: true
        },
        {
          path: Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE.route,
          component: () =>
            import('../views/accountsbalances/NonFungibleBalancePage.vue')
        },
        {
          path: Routes.ACCOUNTS_BALANCES_MANUAL.route,
          component: () =>
            import('../components/accounts/manual-balances/ManualBalances.vue')
        }
      ]
    },
    {
      path: Routes.NFTS.route,
      name: 'nfts',
      component: async () => import('../views/Nft.vue')
    },
    {
      path: Routes.HISTORY.route,
      component: async () => import('../views/history/History.vue'),
      children: [
        {
          path: '',
          redirect: Routes.HISTORY_TRADES.route
        },
        {
          name: 'trades',
          path: Routes.HISTORY_TRADES.route,
          component: async () =>
            import('../views/history/trades/TradeHistory.vue')
        },
        {
          name: 'deposits-withdrawals',
          path: Routes.HISTORY_DEPOSITS_WITHDRAWALS.route,
          component: () =>
            import(
              '../views/history/deposits-withdrawals/DepositsWithdrawals.vue'
            )
        },
        {
          name: 'transactions',
          path: Routes.HISTORY_TRANSACTIONS.route,
          component: () =>
            import('../views/history/transactions/Transactions.vue')
        },
        {
          name: 'ledger-actions',
          path: Routes.HISTORY_LEDGER_ACTIONS.route,
          component: () =>
            import('../views/history/ledger-actions/LedgerActions.vue')
        }
      ]
    },
    {
      path: Routes.DEFI.route,
      component: async () => import('../views/defi/DecentralizedFinance.vue'),
      children: [
        {
          path: '',
          redirect: Routes.DEFI_OVERVIEW.route
        },
        {
          path: Routes.DEFI_OVERVIEW.route,
          component: async () =>
            import('../views/defi/DecentralizedOverview.vue')
        },
        {
          path: Routes.DEFI_DEPOSITS.route,
          component: async () =>
            import('../views/defi/DecentralizedDeposits.vue'),
          children: [
            {
              path: '',
              redirect: Routes.DEFI_DEPOSITS_PROTOCOLS.route
            },
            {
              path: Routes.DEFI_DEPOSITS_PROTOCOLS.route,
              component: async () =>
                import('../views/defi/deposits/Protocols.vue')
            },
            {
              path: Routes.DEFI_DEPOSITS_LIQUIDITY.route,
              component: async () =>
                import('../views/defi/deposits/Liquidity.vue'),
              children: [
                {
                  path: '',
                  redirect: Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP.route
                },
                {
                  path: Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP.route,
                  component: () =>
                    import('../components/defi/uniswap/Uniswap.vue')
                },
                {
                  path: Routes.DEFI_DEPOSITS_LIQUIDITY_BALANCER.route,
                  component: () =>
                    import('../components/defi/balancer/Balancer.vue')
                },
                {
                  path: Routes.DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP.route,
                  component: () =>
                    import('../components/defi/sushiswap/Sushiswap.vue')
                }
              ]
            }
          ]
        },
        {
          path: Routes.DEFI_LIABILITIES.route,
          name: 'defi-liabilities',
          component: async () =>
            import('../views/defi/DecentralizedBorrowing.vue')
        },
        {
          path: Routes.DEFI_DEX_TRADES.route,
          component: async () => import('../views/defi/DexTrades.vue')
        },
        {
          path: Routes.DEFI_AIRDROPS.route,
          component: async () => import('../views/defi/Airdrops.vue')
        }
      ]
    },
    {
      path: Routes.STATISTICS.route,
      name: 'statistics',
      component: async () => import('../views/Statistics.vue')
    },
    {
      path: Routes.STAKING.route,
      component: async () => import('../views/staking/StakingPage.vue'),
      props: route => ({ location: route.params.location ?? null })
    },
    {
      path: Routes.PROFIT_LOSS_REPORTS.route,
      component: async () => import('../views/reports/ProfitLossReports.vue')
    },
    {
      path: Routes.PROFIT_LOSS_REPORT.route,
      component: async () => import('../views/reports/ProfitLossReport.vue'),
      meta: {
        canNavigateBack: true
      }
    },
    {
      path: Routes.ASSET_MANAGER.route,
      component: async () => import('../views/AssetManager.vue'),
      props: route => ({ identifier: route.query.id ?? null })
    },
    {
      path: Routes.PRICE_MANAGER.route,
      component: async () => import('../views/PriceManager.vue'),
      meta: {
        canNavigateBack: true
      },
      props: true
    },
    {
      path: Routes.ETH_ADDRESS_BOOK_MANAGER.route,
      component: async () => import('../views/EthAddressBookManager.vue')
    },
    {
      path: Routes.API_KEYS.route,
      component: async () => import('../views/settings/ApiKeys.vue'),
      children: [
        {
          path: '',
          redirect: Routes.API_KEYS_ROTKI_PREMIUM.route
        },
        {
          path: Routes.API_KEYS_ROTKI_PREMIUM.route,
          component: async () =>
            import('../components/settings/PremiumSettings.vue')
        },
        {
          path: Routes.API_KEYS_EXCHANGES.route,
          component: () =>
            import('../components/settings/api-keys/ExchangeSettings.vue')
        },
        {
          path: Routes.API_KEYS_EXTERNAL_SERVICES.route,
          component: () =>
            import('../components/settings/api-keys/ExternalServices.vue')
        }
      ]
    },
    {
      path: Routes.IMPORT.route,
      name: 'import',
      component: async () => import('../views/ImportData.vue')
    },
    {
      path: Routes.SETTINGS.route,
      component: async () => import('../views/settings/Settings.vue'),
      children: [
        {
          path: '',
          redirect: Routes.SETTINGS_GENERAL.route
        },
        {
          path: Routes.SETTINGS_GENERAL.route,
          component: async () => import('../views/settings/GeneralSettings.vue')
        },
        {
          path: Routes.SETTINGS_ACCOUNTING.route,
          component: async () =>
            import('../views/settings/AccountingSettings.vue')
        },
        {
          path: Routes.SETTINGS_DATA_SECURITY.route,
          component: async () =>
            import('../views/settings/UserSecuritySettings.vue')
        },
        {
          path: Routes.SETTINGS_MODULES.route,
          component: async () => import('../views/settings/ModuleSettings.vue')
        }
      ]
    },
    {
      path: Routes.ASSETS.route,
      component: async () => import('../views/Assets.vue'),
      meta: {
        canNavigateBack: true
      },
      props: true
    },
    {
      path: Routes.LOCATIONS.route,
      component: async () => import('../views/LocationOverview.vue'),
      meta: {
        canNavigateBack: true
      },
      props: true
    },
    ...(process.env.NODE_ENV === 'development'
      ? [
          {
            path: '/playground',
            name: 'playground',
            component: async () => import('../views/dev/Playground.vue')
          }
        ]
      : [])
  ]
});
