import Vue from 'vue';
import Router from 'vue-router';

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
      path: '/tax-report',
      name: 'tax-report',
      component: () => import('../views/TaxReport.vue')
    },
    {
      path: '/otc-trades',
      name: 'otc-trades',
      component: () => import('../views/OtcTrades.vue')
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
          path: 'user-security',
          component: () => import('../views/settings/UserSecuritySettings.vue')
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
      name: 'accounts-balances',
      component: () => import('../views/AccountsBalances.vue'),
      children: [
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
      path: '/defi/lending',
      name: 'defi-lending',
      component: () => import('../views/defi/DecentralizedLending.vue')
    },
    {
      path: '/defi/borrowing',
      name: 'defi-borrowing',
      component: () => import('../views/defi/DecentralizedBorrowing.vue')
    }
  ]
});
