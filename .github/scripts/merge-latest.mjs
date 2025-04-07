import fs from 'node:fs';
import process from 'node:process';
import yaml from 'js-yaml';
import consola from 'consola';

// get two file paths from arguments:
const [, , ...args] = process.argv;
const file1 = args[0];
const file2 = args[1];
const file3 = args[2];

// check that all arguments are present and throw error instead
if (!file1 || !file2 || !file3)
    throw new Error('Please provide 3 file paths as arguments: path to file1, to file2 and destination path');

function exitIfNotExists(file) {
    if (!fs.existsSync(file)) {
        consola.error(`${file} doesn't exist`);
        process.exit(1);
    }
}

// make sure that both input files exist
exitIfNotExists(file1);
exitIfNotExists(file2);

consola.info(`merging ${file1} and ${file2} to ${file3}`);

consola.info(`reading file: ${file1}`);
const yaml1 = yaml.load(fs.readFileSync(file1, 'utf8'));
consola.debug('file content: \n', yaml1);

consola.info(`reading file: ${file2}`);
const yaml2 = yaml.load(fs.readFileSync(file2, 'utf8'));
consola.debug('file content: \n', yaml2);

const merged = { ...yaml1, ...yaml2 };
merged.files.push(...yaml1.files);

consola.debug('merged content: \n', merged);

consola.info(`writing file: ${file3}`);
const mergedYml = yaml.dump(merged);
fs.writeFileSync(file3, mergedYml, 'utf8');
consola.info(`complete`);
