// Create a new DevTools panel
chrome.devtools.panels.create(
  'Rotki Tasks',
  '',
  'panel.html',
  (panel) => {
    console.log('Rotki Task Tracker panel created');
  }
);