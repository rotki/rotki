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
      component: async () => import('../pages/dashboard/index.vue'),
      meta: {
        noteLocation: NoteLocation.DASHBOARD
      }
    },
    {
      path: Routes.ACCOUNTS_BALANCES,
      component: async () => import('../pages/balances/index.vue'),
      children: [
        {
          path: '',
          name: 'accounts-balances',
          redirect: Routes.ACCOUNTS_BALANCES_BLOCKCHAIN
        },
        {
          path: Routes.ACCOUNTS_BALANCES_BLOCKCHAIN,
          name: 'accounts-balances-blockchain',
          component: () => import('../pages/balances/blockchain/index.vue'),
          meta: {
            noteLocation: NoteLocation.ACCOUNTS_BALANCES_BLOCKCHAIN
          }
        },
        {
          path: Routes.ACCOUNTS_BALANCES_EXCHANGE,
          name: 'accounts-balances-exchange',
          component: () => import('../pages/balances/exchange/index.vue'),
          meta: {
            noteLocation: NoteLocation.ACCOUNTS_BALANCES_EXCHANGE
          }
        },
        {
          path: `${Routes.ACCOUNTS_BALANCES_EXCHANGE}/:exchange`,
          component: () => import('../pages/balances/exchange/index.vue'),
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
          component: () => import('../pages/balances/non-fungible/index.vue')
        },
        {
          path: Routes.ACCOUNTS_BALANCES_MANUAL,
          name: 'accounts-balances-manual',
          meta: {
            noteLocation: NoteLocation.ACCOUNTS_BALANCES_MANUAL
          },
          component: () => import('../pages/balances/manual/index.vue')
        }
      ]
    },
    {
      path: Routes.NFTS,
      name: 'nfts',
      meta: {
        noteLocation: NoteLocation.NFTS
      },
      component: async () => import('../pages/nfts/index.vue')
    },
    {
      path: Routes.HISTORY,
      component: async () => import('../pages/history/index.vue'),
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
          component: async () => import('../pages/history/trades/index.vue')
        },
        {
          path: Routes.HISTORY_DEPOSITS_WITHDRAWALS,
          name: 'deposits-withdrawals',
          meta: {
            noteLocation: NoteLocation.HISTORY_DEPOSITS_WITHDRAWALS
          },
          component: () =>
            import('../pages/history/deposits-withdrawals/index.vue')
        },
        {
          path: Routes.HISTORY_TRANSACTIONS,
          name: 'transactions',
          meta: {
            noteLocation: NoteLocation.HISTORY_TRANSACTIONS
          },
          component: () => import('../pages/history/transactions/index.vue')
        },
        {
          path: Routes.HISTORY_LEDGER_ACTIONS,
          name: 'ledger-actions',
          meta: {
            noteLocation: NoteLocation.HISTORY_LEDGER_ACTIONS
          },
          component: () => import('../pages/history/ledger-actions/index.vue')
        }
      ]
    },
    {
      path: Routes.DEFI,
      component: async () => import('../pages/defi/index.vue'),
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
          component: async () => import('../pages/defi/overview/index.vue')
        },
        {
          path: Routes.DEFI_DEPOSITS,
          component: async () => import('../pages/defi/deposits/index.vue'),
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
                import('../pages/defi/deposits/protocols/index.vue')
            },
            {
              path: Routes.DEFI_DEPOSITS_LIQUIDITY,
              component: async () =>
                import('../pages/defi/deposits/liquidity/index.vue'),
              children: [
                {
                  path: '',
                  redirect: Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2
                },
                {
                  path: Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2,
                  component: () =>
                    import(
                      '../pages/defi/deposits/liquidity/uniswap_v2/index.vue'
                    )
                },
                {
                  path: Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3,
                  component: () =>
                    import(
                      '../pages/defi/deposits/liquidity/uniswap_v3/index.vue'
                    )
                },
                {
                  path: Routes.DEFI_DEPOSITS_LIQUIDITY_BALANCER,
                  component: () =>
                    import(
                      '../pages/defi/deposits/liquidity/balancer/index.vue'
                    )
                },
                {
                  path: Routes.DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP,
                  component: () =>
                    import(
                      '../pages/defi/deposits/liquidity/sushiswap/index.vue'
                    )
                }
              ]
            }
          ]
        },
        {
          path: Routes.DEFI_LIABILITIES,
          name: 'defi-liabilities',
          component: async () => import('../pages/defi/liabilities/index.vue')
        },
        {
          path: Routes.DEFI_AIRDROPS,
          component: async () => import('../pages/defi/airdrops/index.vue')
        }
      ]
    },
    {
      path: Routes.STATISTICS,
      name: 'statistics',
      meta: {
        noteLocation: NoteLocation.STATISTICS
      },
      component: async () => import('../pages/statistics/index.vue')
    },
    {
      path: Routes.STAKING,
      meta: {
        noteLocation: NoteLocation.STAKING
      },
      component: async () => import('../pages/staking/index.vue'),
      props: route => ({ location: route.params.location ?? null })
    },
    {
      path: Routes.PROFIT_LOSS_REPORTS,
      meta: {
        noteLocation: NoteLocation.PROFIT_LOSS_REPORTS
      },
      component: async () => import('../pages/reports/index.vue')
    },
    {
      path: Routes.PROFIT_LOSS_REPORT,
      component: async () => import('../pages/report/[id].vue'),
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
      component: async () => import('../pages/asset-manager/index.vue'),
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
            import('../pages/asset-manager/managed/index.vue'),
          props: route => ({ identifier: route.query.id ?? null })
        },
        {
          path: Routes.ASSET_MANAGER_CUSTOM,
          name: 'asset-manager-custom',
          component: async () =>
            import('../pages/asset-manager/custom/index.vue'),
          props: route => ({ identifier: route.query.id ?? null })
        }
      ]
    },
    {
      path: Routes.PRICE_MANAGER,
      component: async () => import('../pages/price-manager/index.vue'),
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
            import('../pages/price-manager/latest/index.vue')
        },
        {
          path: Routes.PRICE_MANAGER_HISTORIC,
          name: 'price-manager-historic',
          component: async () =>
            import('../pages/price-manager/historic/index.vue')
        }
      ]
    },
    {
      path: Routes.ETH_ADDRESS_BOOK_MANAGER,
      meta: {
        noteLocation: NoteLocation.ETH_ADDRESS_BOOK_MANAGER
      },
      component: async () =>
        import('../pages/eth-address-book-manager/index.vue')
    },
    {
      path: Routes.API_KEYS,
      meta: {
        noteLocation: NoteLocation.API_KEYS
      },
      component: async () => import('../pages/settings/api-keys/index.vue'),
      children: [
        {
          path: '',
          redirect: Routes.API_KEYS_ROTKI_PREMIUM
        },
        {
          path: Routes.API_KEYS_ROTKI_PREMIUM,
          component: async () =>
            import('../pages/settings/api-keys/premium/index.vue')
        },
        {
          path: Routes.API_KEYS_EXCHANGES,
          component: () =>
            import('../pages/settings/api-keys/exchanges/index.vue')
        },
        {
          path: Routes.API_KEYS_EXTERNAL_SERVICES,
          component: () =>
            import('../pages/settings/api-keys/external/index.vue')
        }
      ]
    },
    {
      path: Routes.IMPORT,
      name: 'import',
      meta: {
        noteLocation: NoteLocation.IMPORT
      },
      component: async () => import('../pages/import/index.vue')
    },
    {
      path: Routes.SETTINGS,
      component: async () => import('../pages/settings/index.vue'),
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
          component: async () => import('../pages/settings/general/index.vue')
        },
        {
          path: Routes.SETTINGS_ACCOUNTING,
          meta: {
            noteLocation: NoteLocation.SETTINGS_ACCOUNTING
          },
          component: async () =>
            import('../pages/settings/accounting/index.vue')
        },
        {
          path: Routes.SETTINGS_DATA_SECURITY,
          meta: {
            noteLocation: NoteLocation.SETTINGS_DATA_SECURITY
          },
          component: async () =>
            import('../pages/settings/data-security/index.vue')
        },
        {
          path: Routes.SETTINGS_MODULES,
          meta: {
            noteLocation: NoteLocation.SETTINGS_MODULES
          },
          component: async () => import('../pages/settings/modules/index.vue')
        }
      ]
    },
    {
      path: Routes.ASSETS,
      component: async () => import('../pages/assets/[identifier].vue'),
      meta: {
        canNavigateBack: true,
        noteLocation: NoteLocation.ASSETS
      },
      props: true
    },
    {
      path: Routes.LOCATIONS,
      component: async () => import('../pages/locations/[identifier].vue'),
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
            component: async () => import('../pages/playground/index.vue')
          }
        ]
      : [])
  ]
});
