import { startPromise } from '@shared/utils';
import { createRouter, createWebHashHistory, type RouteLocationRaw } from 'vue-router';
import { handleHotUpdate, routes } from 'vue-router/auto-routes';
import NotFound from '@/pages/404.vue';
import { useSessionAuthStore } from '@/store/session/auth';

const base = import.meta.env.VITE_PUBLIC_PATH ? window.location.pathname : '/';

const errorRoutes = [
  {
    component: NotFound,
    meta: {
      title: '404 Not Found',
    },
    name: 'NotFound',
    path: '/:pathMatch(.*)*',
  },
];

const allRoutes = [
  ...routes,
  ...errorRoutes,
];

export const router = createRouter({
  history: createWebHashHistory(base),
  routes: allRoutes,
  scrollBehavior: (to, from, savedPosition) => {
    if (to.hash) {
      const element = document.getElementById(to.hash.replace(/#/, ''));
      if (element) {
        setTimeout(() => {
          startPromise(nextTick(() => {
            document.body.scrollTo({
              behavior: 'smooth',
              left: 0,
              top: element.offsetTop - 80,
            });
          }));
        }, 200);
      }

      return { el: to.hash };
    }
    else if (savedPosition && !(savedPosition.left === 0 && savedPosition.left === 0)) {
      document.body.scrollTo(savedPosition.left, savedPosition.top);
      return savedPosition;
    }

    if (from.path !== to.path && !to.query.keepScrollPosition) {
      document.body.scrollTo(0, 0);
      return { left: 0, top: 0 };
    }
  },
});

const userRoutes: RouteLocationRaw[] = ['/user/create', '/user/login', '/user'];

router.beforeEach((to, from, next) => {
  document.title = to.meta?.title ? to.meta.title.toString() : 'rotki';

  const store = useSessionAuthStore();
  const logged = store.logged;
  if (logged) {
    if (userRoutes.includes(to.path))
      return next('/dashboard');

    next();
  }
  else if (to.path.startsWith('/user') || to.path === '/wallet-bridge') {
    next();
  }
  else {
    next('/user/login');
  }
});

if (import.meta.hot)
  handleHotUpdate(router);
