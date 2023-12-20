const fs = require('node:fs');
const axios = require('axios');
const { externalLinks } = require('./../src/data/external-links.js');

const processDynamicUrl = url =>
  // Format dynamic URL and replace with valid value.
  url.replace('$version', '1.31.1');

async function checkLink(rawUrl) {
  const url = processDynamicUrl(rawUrl);
  try {
    const response = await axios.get(url);
    if (response.status === 200) {
      console.log(`External link ${url} returned a 200 status code.`);
    } else {
      console.error(
        `External link ${url} returned a non-200 status code: ${response.status}`
      );
      fs.unlinkSync('./src/data/external-links.js');
      process.exit(1); // Exit with an error status code
    }
  } catch (error) {
    console.error(`Error checking link ${url}: ${error.message}`);
    fs.unlinkSync('./src/data/external-links.js');
    process.exit(1); // Exit with an error status code
  }
}

function getFlattenedValues(obj) {
  return Object.values(obj).flatMap(value =>
    typeof value === 'object' && value !== null ? Object.values(value) : value
  );
}

// Create an array of promises
const linkCheckPromises = getFlattenedValues(externalLinks).map(checkLink);

// Wait for all promises to settle
Promise.all(linkCheckPromises)
  .then(() => {
    console.log('\u001B[32m', 'All external links verified');
    process.exit(0);
  })
  .finally(() => {
    fs.unlinkSync('./src/data/external-links.js');
  });
