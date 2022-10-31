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
      redirect: Routes.ROOT
    },
    {
      path: Routes.DASHBOARD,
      alias: Routes.ROOT,
      name: 'dashboard',
      component: async () => import('../views/Dashboard.vue'),
      meta: {
        noteLocation: NoteLocation.DASHBOARD
      }
    },
    {
      path: Routes.ACCOUNTS_BALANCES,
      component: async () => import('../views/AccountsBalances.vue'),
      children: [
        {
          path: '',
          name: 'accounts-balances',
          redirect: Routes.ACCOUNTS_BALANCES_BLOCKCHAIN
        },
        {
          path: Routes.ACCOUNTS_BALANCES_BLOCKCHAIN,
          name: 'accounts-balances-blockchain',
          component: () =>
            import('../components/accounts/BlockchainBalances.vue'),
          meta: {
            noteLocation: NoteLocation.ACCOUNTS_BALANCES_BLOCKCHAIN
          }
        },
        {
          path: Routes.ACCOUNTS_BALANCES_EXCHANGE,
          name: 'accounts-balances-exchange',
          component: () =>
            import('../components/accounts/exchanges/ExchangeBalances.vue'),
          meta: {
            noteLocation: NoteLocation.ACCOUNTS_BALANCES_EXCHANGE
          }
        },
        {
          path: `${Routes.ACCOUNTS_BALANCES_EXCHANGE}/:exchange`,
          component: () =>
            import('../components/accounts/exchanges/ExchangeBalances.vue'),
          meta: {
            noteLocation: NoteLocation.ACCOUNTS_BALANCES_EXCHANGE
          },
          props: true
        },
        {
          path: Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE,
          name: 'accounts-balances-non-fungible',
          meta: {
            noteLocation: NoteLocation.ACCOUNTS_BALANCES_NON_FUNGIBLE
          },
          component: () =>
            import('../views/accountsbalances/NonFungibleBalancePage.vue')
        },
        {
          path: Routes.ACCOUNTS_BALANCES_MANUAL,
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
      path: Routes.NFTS,
      name: 'nfts',
      meta: {
        noteLocation: NoteLocation.NFTS
      },
      component: async () => import('../views/Nft.vue')
    },
    {
      path: Routes.HISTORY,
      component: async () => import('../views/history/History.vue'),
      children: [
        {
          path: '',
          name: 'history',
          redirect: Routes.HISTORY_TRADES
        },
        {
          path: Routes.HISTORY_TRADES,
          name: 'trades',
          meta: {
            noteLocation: NoteLocation.HISTORY_TRADES
          },
          component: async () =>
            import('../views/history/trades/TradeHistory.vue')
        },
        {
          path: Routes.HISTORY_DEPOSITS_WITHDRAWALS,
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
          path: Routes.HISTORY_TRANSACTIONS,
          name: 'transactions',
          meta: {
            noteLocation: NoteLocation.HISTORY_TRANSACTIONS
          },
          component: () =>
            import('../views/history/transactions/Transactions.vue')
        },
        {
          path: Routes.HISTORY_LEDGER_ACTIONS,
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
      path: Routes.DEFI,
      component: async () => import('../views/defi/DecentralizedFinance.vue'),
      meta: {
        noteLocation: NoteLocation.DEFI
      },
      children: [
        {
          path: '',
          name: 'defi',
          redirect: Routes.DEFI_OVERVIEW
        },
        {
          path: Routes.DEFI_OVERVIEW,
          name: 'defi-overview',
          component: async () =>
            import('../views/defi/DecentralizedOverview.vue')
        },
        {
          path: Routes.DEFI_DEPOSITS,
          component: async () =>
            import('../views/defi/DecentralizedDeposits.vue'),
          children: [
            {
              path: '',
              name: 'defi-deposits',
              redirect: Routes.DEFI_DEPOSITS_PROTOCOLS
            },
            {
              path: Routes.DEFI_DEPOSITS_PROTOCOLS,
              name: 'defi-deposits-protocols',
              component: async () =>
                import('../views/defi/deposits/Protocols.vue')
            },
            {
              path: Routes.DEFI_DEPOSITS_LIQUIDITY,
              component: async () =>
                import('../views/defi/deposits/Liquidity.vue'),
              children: [
                {
                  path: '',
                  redirect: Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2
                },
                {
                  path: Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2,
                  component: () =>
                    import('../components/defi/uniswap/UniswapV2.vue')
                },
                {
                  path: Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3,
                  component: () =>
                    import('../components/defi/uniswap/UniswapV3.vue')
                },
                {
                  path: Routes.DEFI_DEPOSITS_LIQUIDITY_BALANCER,
                  component: () =>
                    import('../components/defi/balancer/Balancer.vue')
                },
                {
                  path: Routes.DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP,
                  component: () =>
                    import('../components/defi/sushiswap/Sushiswap.vue')
                }
              ]
            }
          ]
        },
        {
          path: Routes.DEFI_LIABILITIES,
          name: 'defi-liabilities',
          component: async () =>
            import('../views/defi/DecentralizedBorrowing.vue')
        },
        {
          path: Routes.DEFI_AIRDROPS,
          component: async () => import('../views/defi/Airdrops.vue')
        }
      ]
    },
    {
      path: Routes.STATISTICS,
      name: 'statistics',
      meta: {
        noteLocation: NoteLocation.STATISTICS
      },
      component: async () => import('../views/Statistics.vue')
    },
    {
      path: Routes.STAKING,
      meta: {
        noteLocation: NoteLocation.STAKING
      },
      component: async () => import('../views/staking/StakingPage.vue'),
      props: route => ({ location: route.params.location ?? null })
    },
    {
      path: Routes.PROFIT_LOSS_REPORTS,
      meta: {
        noteLocation: NoteLocation.PROFIT_LOSS_REPORTS
      },
      component: async () => import('../views/reports/ProfitLossReports.vue')
    },
    {
      path: Routes.PROFIT_LOSS_REPORT,
      component: async () => import('../views/reports/ProfitLossReport.vue'),
      meta: {
        canNavigateBack: true,
        noteLocation: NoteLocation.PROFIT_LOSS_REPORTS
      }
    },
    {
      path: Routes.ASSET_MANAGER,
      meta: {
        noteLocation: NoteLocation.ASSETS
      },
      component: async () => import('../views/assets/AssetManager.vue'),
      children: [
        {
          path: '',
          name: 'asset-manager',
          redirect: Routes.ASSET_MANAGER_MANAGED
        },
        {
          path: Routes.ASSET_MANAGER_MANAGED,
          name: 'asset-manager-managed',
          component: async () =>
            import('../views/assets/ManagedAssetsManagement.vue'),
          props: route => ({ identifier: route.query.id ?? null })
        },
        {
          path: Routes.ASSET_MANAGER_CUSTOM,
          name: 'asset-manager-custom',
          component: async () =>
            import('../views/assets/CustomAssetsManagement.vue'),
          props: route => ({ identifier: route.query.id ?? null })
        }
      ]
    },
    {
      path: Routes.PRICE_MANAGER,
      component: async () => import('../views/prices/PriceManager.vue'),
      meta: {
        canNavigateBack: true,
        noteLocation: NoteLocation.PRICE_MANAGER
      },
      props: true,
      children: [
        {
          path: '',
          name: 'price-manager',
          redirect: Routes.PRICE_MANAGER_LATEST
        },
        {
          path: Routes.PRICE_MANAGER_LATEST,
          name: 'price-manager-current',
          component: async () =>
            import('../views/prices/LatestPriceManagement.vue')
        },
        {
          path: Routes.PRICE_MANAGER_HISTORIC,
          name: 'price-manager-historic',
          component: async () =>
            import('../views/prices/HistoricPriceManagement.vue')
        }
      ]
    },
    {
      path: Routes.ETH_ADDRESS_BOOK_MANAGER,
      meta: {
        noteLocation: NoteLocation.ETH_ADDRESS_BOOK_MANAGER
      },
      component: async () => import('../views/EthAddressBookManager.vue')
    },
    {
      path: Routes.API_KEYS,
      meta: {
        noteLocation: NoteLocation.API_KEYS
      },
      component: async () => import('../views/settings/ApiKeys.vue'),
      children: [
        {
          path: '',
          redirect: Routes.API_KEYS_ROTKI_PREMIUM
        },
        {
          path: Routes.API_KEYS_ROTKI_PREMIUM,
          component: async () =>
            import('../components/settings/PremiumSettings.vue')
        },
        {
          path: Routes.API_KEYS_EXCHANGES,
          component: () =>
            import('../components/settings/api-keys/ExchangeSettings.vue')
        },
        {
          path: Routes.API_KEYS_EXTERNAL_SERVICES,
          component: () =>
            import('../components/settings/api-keys/ExternalServices.vue')
        }
      ]
    },
    {
      path: Routes.IMPORT,
      name: 'import',
      meta: {
        noteLocation: NoteLocation.IMPORT
      },
      component: async () => import('../views/ImportData.vue')
    },
    {
      path: Routes.SETTINGS,
      component: async () => import('../views/settings/Settings.vue'),
      children: [
        {
          path: '',
          redirect: Routes.SETTINGS_GENERAL
        },
        {
          path: Routes.SETTINGS_GENERAL,
          meta: {
            noteLocation: NoteLocation.SETTINGS_GENERAL
          },
          component: async () => import('../views/settings/GeneralSettings.vue')
        },
        {
          path: Routes.SETTINGS_ACCOUNTING,
          meta: {
            noteLocation: NoteLocation.SETTINGS_ACCOUNTING
          },
          component: async () =>
            import('../views/settings/AccountingSettings.vue')
        },
        {
          path: Routes.SETTINGS_DATA_SECURITY,
          meta: {
            noteLocation: NoteLocation.SETTINGS_DATA_SECURITY
          },
          component: async () =>
            import('../views/settings/UserSecuritySettings.vue')
        },
        {
          path: Routes.SETTINGS_MODULES,
          meta: {
            noteLocation: NoteLocation.SETTINGS_MODULES
          },
          component: async () => import('../views/settings/ModuleSettings.vue')
        }
      ]
    },
    {
      path: Routes.ASSETS,
      component: async () => import('../views/Assets.vue'),
      meta: {
        canNavigateBack: true,
        noteLocation: NoteLocation.ASSETS
      },
      props: true
    },
    {
      path: Routes.LOCATIONS,
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
