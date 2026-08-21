import fs from 'node:fs';
import process from 'node:process';
import { dump, load } from 'js-yaml';
import consola from 'consola';

// get two file paths from arguments:
const [, , ...args] = process.argv;
const file1 = args[0];
const file2 = args[1];
const file3 = args[2];

// check that all arguments are present and throw error instead
if (!file1 || !file2 || !file3)
    throw new Error('Please provide 3 file paths as arguments: path to file1, to file2 and destination path');

function fail(message) {
    consola.error(message);
    process.exit(1);
}

/**
 * Reads an electron-updater manifest and checks it carries the fields the merge relies on.
 * A malformed input would otherwise surface as a bare TypeError, or worse, produce a manifest
 * that silently points auto-update at nothing.
 */
function readManifest(file) {
    if (!fs.existsSync(file))
        fail(`${file} doesn't exist`);

    consola.info(`reading file: ${file}`);

    let manifest;
    try {
        manifest = load(fs.readFileSync(file, 'utf8'));
    }
    catch (error) {
        fail(`${file} is not valid yaml: ${error.message}`);
    }

    if (typeof manifest !== 'object' || manifest === null || Array.isArray(manifest))
        fail(`${file} does not contain a yaml mapping`);

    if (typeof manifest.version !== 'string')
        fail(`${file} has no version`);

    if (!Array.isArray(manifest.files) || manifest.files.length === 0)
        fail(`${file} has no files entries`);

    consola.debug('file content: \n', manifest);
    return manifest;
}

consola.info(`merging ${file1} and ${file2} to ${file3}`);

const yaml1 = readManifest(file1);
const yaml2 = readManifest(file2);

// merging two manifests of different versions would hand auto-update a mix of builds
if (yaml1.version !== yaml2.version)
    fail(`version mismatch: ${file1} is ${yaml1.version} but ${file2} is ${yaml2.version}`);

// yaml2 wins on the top level fields; its files come first, as before
const merged = { ...yaml1, ...yaml2, files: [...yaml2.files, ...yaml1.files] };

consola.debug('merged content: \n', merged);

consola.info(`writing file: ${file3}`);
const mergedYml = dump(merged);
fs.writeFileSync(file3, mergedYml, 'utf8');
consola.info(`complete`);
