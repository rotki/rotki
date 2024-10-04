/* istanbul ignore file */

import { setupLayouts } from 'virtual:generated-layouts';
import { type RouteLocationRaw, createRouter, createWebHashHistory } from 'vue-router';
import { handleHotUpdate, routes } from 'vue-router/auto-routes';

const base = import.meta.env.VITE_PUBLIC_PATH ? window.location.pathname : '/';

export const router = createRouter({
  history: createWebHashHistory(base),
  scrollBehavior: (to, from, savedPosition) => {
    if (to.hash) {
      const element = document.getElementById(to.hash.replace(/#/, ''));
      if (element) {
        setTimeout(() => {
          startPromise(nextTick(() => {
            document.body.scrollTo({
              left: 0,
              top: element.offsetTop - 80,
              behavior: 'smooth',
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
      return { top: 0, left: 0 };
    }
  },
  routes: setupLayouts(routes),
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
