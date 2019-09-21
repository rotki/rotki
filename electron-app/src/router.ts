import Vue from 'vue';
import Router from 'vue-router';

Vue.use(Router);

export default new Router({
  mode: 'history',
  base: process.env.BASE_URL,
  routes: [
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
      path: '/settings/user',
      name: 'user-settings',
      component: () => import('./views/settings/User.vue')
    },
    {
      path: '/exchange-balances/:exchange',
      name: 'exchange-balances',
      component: () => import('./views/ExchangeBalances.vue')
    }
  ]
});
