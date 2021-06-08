self.addEventListener('message', async e => {
  if (!e.data) {
    return;
  }

  switch (e.data) {
    case 'skipWaiting':
      await self.skipWaiting();
      break;
    default:
      break;
  }
});
