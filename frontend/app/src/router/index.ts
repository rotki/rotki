/* istanbul ignore file */

import { setupLayouts } from 'virtual:generated-layouts';
import { type RouteLocationRaw, createRouter, createWebHashHistory } from 'vue-router';
import { handleHotUpdate, routes } from 'vue-router/auto-routes';
import { startPromise } from '@shared/utils';
import { useSessionAuthStore } from '@/store/session/auth';

const base = import.meta.env.VITE_PUBLIC_PATH ? window.location.pathname : '/';

export const router = createRouter({
  history: createWebHashHistory(base),
  routes: setupLayouts(routes),
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
  const store = useSessionAuthStore();
  const logged = store.logged;
  if (logged) {
    if (userRoutes.includes(to.path))
      return next('/dashboard');

    next();
  }
  else if (to.path.startsWith('/user')) {
    next();
  }
  else {
    next('/user/login');
  }
});

if (import.meta.hot)
  handleHotUpdate(router);
