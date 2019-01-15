import {Application, SpectronClient} from 'spectron';
import * as electron from 'electron';
import * as path from 'path';
import * as fs from 'fs';
const retry = require('promise-retry');

export const GLOBAL_TIMEOUT = 120_000;
export const METHOD_TIMEOUT = 40_000;

type AsyncBlock = () => Promise<void>;

export function initialiseSpectron() {

    return new Application({
        path: electron as any,
        args: [path.join(__dirname, '../..')],
        env: {
            ELECTRON_ENABLE_LOGGING: true,
            ELECTRON_ENABLE_STACK_DUMPING: true,
            NODE_ENV: 'development',
            SPECTRON: true
        },
        startTimeout: METHOD_TIMEOUT,
        connectionRetryTimeout: GLOBAL_TIMEOUT,
        waitTimeout: METHOD_TIMEOUT,
        chromeDriverLogPath: '../chromedriverlog.txt'
    });
}

export async function createAccount(app: Application, username: string, password: string) {
    await app.client.waitUntilTextExists('.jconfirm-title', 'Sign In', METHOD_TIMEOUT);

    await app.client.click('.jconfirm-buttons :nth-child(2)');

    await app.client.waitForExist('#repeat_password_entry', METHOD_TIMEOUT);

    await app.client.addValue('#user_name_entry', username);
    await app.client.addValue('#password_entry', password);
    await app.client.addValue('#repeat_password_entry', password);

    await app.client.click('.jconfirm-buttons>button');

    await app.client.waitUntilTextExists('div', `Welcome ${username}!`, METHOD_TIMEOUT);
    await app.client.waitUntilTextExists('div', `Welcome to Rotkehlchen!`, METHOD_TIMEOUT);

    await app.client.execute(() => {
        // noinspection JSJQueryEfficiency
        $('.jconfirm-buttons>button').click();
        // noinspection JSJQueryEfficiency
        $('.jconfirm-buttons>button').click();
    });

    await app.client.waitForVisible('.jconfirm', METHOD_TIMEOUT, true);
}

export async function navigateTo(client: SpectronClient, elementId: string) {
    await client.click('#user-dropdown');
    await client.waitForVisible(elementId, METHOD_TIMEOUT);
    await client.click(elementId);
    await client.pause(100);
}

export async function closeAddYourSettingsPopup(client: SpectronClient) {
    await client.waitUntilTextExists('.jconfirm-title', 'Add your settings', METHOD_TIMEOUT);
    await retry( async() => {
        client.click('.jconfirm-buttons>button');
    });
}

export async function logout(client: SpectronClient) {
    await retry( async() => {
        client.click('#user-dropdown');
    });
    await client.waitForVisible('#logout_button', METHOD_TIMEOUT);
    await retry( async() => {
        client.click('#logout_button');
    });

    await client.waitForVisible('.jconfirm', METHOD_TIMEOUT);
    await retry( async() => {
        client.click('.jconfirm-buttons>button');
    });
    await client.waitUntilTextExists('.jconfirm-title', 'Sign In', METHOD_TIMEOUT);
}

export async function login(client: SpectronClient, username: string, password: string) {
    await client.clearElement('#username_entry');
    await client.addValue('#username_entry', username);

    await client.clearElement('#password_entry');
    await client.addValue('#password_entry', password);

    await retry( async() => {
        client.click('.jconfirm-buttons>button');
    });

    await client.waitUntilTextExists('.jconfirm-title', 'Successful Sign In', METHOD_TIMEOUT);
    await retry( async() => {
        client.click('.jconfirm-buttons>button');
    });
    await client.waitForVisible('.jconfirm', METHOD_TIMEOUT, true);
}

export function takeScreenshot(app: Application, title: string): Promise<void> {
    const filename = getScreenshotFilename(title);
    return new Promise<void>((resolve, reject) => {
        app.browserWindow.capturePage().then(imageBuffer => {
            fs.writeFile(filename, imageBuffer, (err: Error) => {
                if (err) {
                    console.log(err);
                    reject(err);
                } else {
                    console.log(`Took screenshot: ${title}`);
                    resolve();
                }
            });
        });
    });
}

function getScreenshotFilename(title: string) {
    const directory = 'failure-screenshots';
    if (!fs.existsSync(directory)) {
        fs.mkdirSync(directory);
    }
    return `${directory}/${title.replace(/\s/g, '_')}.png`;
}

export async function setupTest(app: Application, title: string, block: AsyncBlock): Promise<void> {
    try {
        await block();
    } catch (e) {
        await takeScreenshot(app, title);
        throw e;
    }
}

export async function captureOnFailure(app: Application, currentTest?: Mocha.Test) {
    if (currentTest && currentTest.state === 'failed') {
        await takeScreenshot(app, currentTest.title);
    }
}
