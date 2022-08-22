/* istanbul ignore file */

import Vue from 'vue';
import Router from 'vue-router';
import { Routes } from '@/router/routes';
import { NoteLocation } from '@/types/notes';
import { checkIfDevelopment } from '@/utils/env-utils';

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
    document.body.scrollTo(0, 0);
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
      component: async () => import('../views/Dashboard.vue'),
      meta: {
        noteLocation: NoteLocation.DASHBOARD
      }
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
          name: 'accounts-balances-blockchain',
          component: () =>
            import('../components/accounts/BlockchainBalances.vue'),
          meta: {
            noteLocation: NoteLocation.ACCOUNTS_BALANCES_BLOCKCHAIN
          }
        },
        {
          path: Routes.ACCOUNTS_BALANCES_EXCHANGE.route,
          name: 'accounts-balances-exchange',
          component: () =>
            import('../components/accounts/exchanges/ExchangeBalances.vue'),
          meta: {
            noteLocation: NoteLocation.ACCOUNTS_BALANCES_EXCHANGE
          }
        },
        {
          path: `${Routes.ACCOUNTS_BALANCES_EXCHANGE.route}/:exchange`,
          component: () =>
            import('../components/accounts/exchanges/ExchangeBalances.vue'),
          meta: {
            noteLocation: NoteLocation.ACCOUNTS_BALANCES_EXCHANGE
          },
          props: true
        },
        {
          path: Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE.route,
          name: 'accounts-balances-non-fungible',
          meta: {
            noteLocation: NoteLocation.ACCOUNTS_BALANCES_NON_FUNGIBLE
          },
          component: () =>
            import('../views/accountsbalances/NonFungibleBalancePage.vue')
        },
        {
          path: Routes.ACCOUNTS_BALANCES_MANUAL.route,
          name: 'accounts-balances-manual',
          meta: {
            noteLocation: NoteLocation.ACCOUNTS_BALANCES_MANUAL
          },
          component: () =>
            import('../components/accounts/manual-balances/ManualBalances.vue')
        }
      ]
    },
    {
      path: Routes.NFTS.route,
      name: 'nfts',
      meta: {
        noteLocation: NoteLocation.NFTS
      },
      component: async () => import('../views/Nft.vue')
    },
    {
      path: Routes.HISTORY.route,
      component: async () => import('../views/history/History.vue'),
      children: [
        {
          path: '',
          name: 'history',
          redirect: Routes.HISTORY_TRADES.route
        },
        {
          path: Routes.HISTORY_TRADES.route,
          name: 'trades',
          meta: {
            noteLocation: NoteLocation.HISTORY_TRADES
          },
          component: async () =>
            import('../views/history/trades/TradeHistory.vue')
        },
        {
          path: Routes.HISTORY_DEPOSITS_WITHDRAWALS.route,
          name: 'deposits-withdrawals',
          meta: {
            noteLocation: NoteLocation.HISTORY_DEPOSITS_WITHDRAWALS
          },
          component: () =>
            import(
              '../views/history/deposits-withdrawals/DepositsWithdrawals.vue'
            )
        },
        {
          path: Routes.HISTORY_TRANSACTIONS.route,
          name: 'transactions',
          meta: {
            noteLocation: NoteLocation.HISTORY_TRANSACTIONS
          },
          component: () =>
            import('../views/history/transactions/Transactions.vue')
        },
        {
          path: Routes.HISTORY_LEDGER_ACTIONS.route,
          name: 'ledger-actions',
          meta: {
            noteLocation: NoteLocation.HISTORY_LEDGER_ACTIONS
          },
          component: () =>
            import('../views/history/ledger-actions/LedgerActions.vue')
        }
      ]
    },
    {
      path: Routes.DEFI.route,
      component: async () => import('../views/defi/DecentralizedFinance.vue'),
      meta: {
        noteLocation: NoteLocation.DEFI
      },
      children: [
        {
          path: '',
          name: 'defi',
          redirect: Routes.DEFI_OVERVIEW.route
        },
        {
          path: Routes.DEFI_OVERVIEW.route,
          name: 'defi-overview',
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
              name: 'defi-deposits',
              redirect: Routes.DEFI_DEPOSITS_PROTOCOLS.route
            },
            {
              path: Routes.DEFI_DEPOSITS_PROTOCOLS.route,
              name: 'defi-deposits-protocols',
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
                  redirect: Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2.route
                },
                {
                  path: Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2.route,
                  component: () =>
                    import('../components/defi/uniswap/UniswapV2.vue')
                },
                {
                  path: Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3.route,
                  component: () =>
                    import('../components/defi/uniswap/UniswapV3.vue')
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
      meta: {
        noteLocation: NoteLocation.STATISTICS
      },
      component: async () => import('../views/Statistics.vue')
    },
    {
      path: Routes.STAKING.route,
      meta: {
        noteLocation: NoteLocation.STAKING
      },
      component: async () => import('../views/staking/StakingPage.vue'),
      props: route => ({ location: route.params.location ?? null })
    },
    {
      path: Routes.PROFIT_LOSS_REPORTS.route,
      meta: {
        noteLocation: NoteLocation.PROFIT_LOSS_REPORTS
      },
      component: async () => import('../views/reports/ProfitLossReports.vue')
    },
    {
      path: Routes.PROFIT_LOSS_REPORT.route,
      component: async () => import('../views/reports/ProfitLossReport.vue'),
      meta: {
        canNavigateBack: true,
        noteLocation: NoteLocation.PROFIT_LOSS_REPORTS
      }
    },
    {
      path: Routes.ASSET_MANAGER.route,
      meta: {
        noteLocation: NoteLocation.ASSETS
      },
      component: async () => import('../views/AssetManager.vue'),
      props: route => ({ identifier: route.query.id ?? null })
    },
    {
      path: Routes.PRICE_MANAGER.route,
      component: async () => import('../views/PriceManager.vue'),
      meta: {
        canNavigateBack: true,
        noteLocation: NoteLocation.PRICE_MANAGER
      },
      props: true
    },
    {
      path: Routes.ETH_ADDRESS_BOOK_MANAGER.route,
      meta: {
        noteLocation: NoteLocation.ETH_ADDRESS_BOOK_MANAGER
      },
      component: async () => import('../views/EthAddressBookManager.vue')
    },
    {
      path: Routes.API_KEYS.route,
      meta: {
        noteLocation: NoteLocation.API_KEYS
      },
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
      meta: {
        noteLocation: NoteLocation.IMPORT
      },
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
          meta: {
            noteLocation: NoteLocation.SETTINGS_GENERAL
          },
          component: async () => import('../views/settings/GeneralSettings.vue')
        },
        {
          path: Routes.SETTINGS_ACCOUNTING.route,
          meta: {
            noteLocation: NoteLocation.SETTINGS_ACCOUNTING
          },
          component: async () =>
            import('../views/settings/AccountingSettings.vue')
        },
        {
          path: Routes.SETTINGS_DATA_SECURITY.route,
          meta: {
            noteLocation: NoteLocation.SETTINGS_DATA_SECURITY
          },
          component: async () =>
            import('../views/settings/UserSecuritySettings.vue')
        },
        {
          path: Routes.SETTINGS_MODULES.route,
          meta: {
            noteLocation: NoteLocation.SETTINGS_MODULES
          },
          component: async () => import('../views/settings/ModuleSettings.vue')
        }
      ]
    },
    {
      path: Routes.ASSETS.route,
      component: async () => import('../views/Assets.vue'),
      meta: {
        canNavigateBack: true,
        noteLocation: NoteLocation.ASSETS
      },
      props: true
    },
    {
      path: Routes.LOCATIONS.route,
      component: async () => import('../views/LocationOverview.vue'),
      meta: {
        canNavigateBack: true,
        noteLocation: NoteLocation.LOCATIONS
      },
      props: true
    },
    ...(checkIfDevelopment()
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
