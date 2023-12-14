import axios from 'axios';
import { externalLinks } from './externalLinks'

async function checkLink(url) {
  try {
    const response = await axios.get(url);
    if (response.status === 200) {
      console.log(`Link ${url} returned a 200 status code.`);
    } else {
      console.error(`Link ${url} returned a non-200 status code: ${response.status}`);
      process.exit(1); // Exit with an error status code
    }
  } catch (error) {
    console.error(`Error checking link ${url}: ${error.message}`);
    process.exit(1); // Exit with an error status code
  }
}

// Check each link
Object.values(externalLinks).forEach(checkLink);
