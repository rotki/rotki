import Vue from 'vue';
import Router from 'vue-router';

Vue.use(Router);

export default new Router({
  mode: 'history',
  base: process.env.BASE_URL,
  routes: [
    {
      path: '*',
      redirect: '/'
    },
    {
      path: '/',
      name: 'dashboard',
      component: () => import('./views/Dashboard.vue')
    },
    {
      path: '/statistics',
      name: 'statistics',
      component: () => import('./views/Statistics.vue')
    },
    {
      path: '/tax-report',
      name: 'tax-report',
      component: () => import('./views/TaxReport.vue')
    },
    {
      path: '/otc-trades',
      name: 'otc-trades',
      component: () => import('./views/OtcTrades.vue')
    },
    {
      path: '/settings/accounting',
      name: 'accounting-settings',
      component: () => import('./views/settings/Accounting.vue')
    },
    {
      path: '/settings/general',
      name: 'general-settings',
      component: () => import('./views/settings/General.vue')
    },
    {
      path: '/settings/api-keys',
      name: 'api-keys',
      component: () => import('./views/settings/ApiKeys.vue')
    },
    {
      path: '/exchange-balances/:exchange',
      name: 'exchange-balances',
      component: () => import('./views/ExchangeBalances.vue')
    },
    {
      path: '/import',
      name: 'import',
      component: () => import('./views/ImportData.vue')
    },
    {
      path: '/blockchain-accounts',
      name: 'blockchain-accounts',
      component: () => import('./views/AccountsBalances.vue')
    }
  ]
});
