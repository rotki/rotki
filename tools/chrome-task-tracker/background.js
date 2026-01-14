// Background service worker for Rotki Task Tracker
// This service worker handles extension lifecycle events

chrome.runtime.onInstalled.addListener(() => {
  console.log('Rotki Async Task Tracker installed');
});

// Keep the service worker alive if needed
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'ping') {
    sendResponse({ status: 'ok' });
  }
  return true;
});