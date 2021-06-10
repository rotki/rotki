/* eslint-disable no-console */
/* istanbul ignore file */

import { register } from 'register-service-worker';

if (
  process.env.NODE_ENV === 'production' &&
  'serviceWorker' in navigator &&
  !('interop' in window)
) {
  console.info('Registering service worker');
  register('./service-worker.js', {
    ready() {
      console.log(
        'App is being served from cache by a service worker.\n' +
          'For more details, visit https://goo.gl/AFskqB'
      );
    },
    registered(registration: ServiceWorkerRegistration) {
      // Check periodically for updates every minute
      setInterval(async () => {
        await registration.update();
      }, 1000 * 60);
      console.log('Service worker has been registered.');
    },
    cached() {
      console.log('Content has been cached for offline use.');
    },
    updatefound() {
      console.log('New content is downloading.');
    },
    updated(registration: ServiceWorkerRegistration) {
      document.dispatchEvent(
        new CustomEvent('swUpdated', { detail: registration })
      );
      console.log('New content is available; please refresh.');
    },
    offline() {
      console.log(
        'No internet connection found. App is running in offline mode.'
      );
    },
    error(error: Error) {
      console.error('Error during service worker registration:', error);
    }
  });
}
