const fs = require('node:fs');
const path = require('node:path');

/**
 * This is a hacky way to work around bignumber.js and vues's
 * wrapping unwrapping limitations with private fields.
 * https://github.com/vuejs/core/issues/2981
 *
 * bignumber.js has a single private readonly property which messes with the
 * inference when wrapping/unwrapping it to a ref.
 *
 * This script "patches" the file by removing the private modifier from the
 * property to remove the need for casting to maintain the types.
 */

const file = 'node_modules/bignumber.js/bignumber.d.ts';

const dtsPath = path.join(process.cwd(), file);

fs.readFile(dtsPath, { encoding: 'utf8' }, (err, data) => {
  const formatted = data.replace(
    /private readonly _isBigNumber: true/g,
    'readonly _isBigNumber: true'
  );
  fs.writeFile(dtsPath, formatted, 'utf8', err => {
    if (err) return console.log(err);
  });
});
