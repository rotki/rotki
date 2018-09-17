// Nice overview for electron tests with the chai.should model:
// https://dzone.com/articles/write-automated-tests-for-electron-with-spectron-m

const {
    path, chai, Application, electronPath, waitAfterLoad, waitAfterSignup
} = require('./utils/setup')

const guid = () => {
    const s4 = () => Math.floor((1 + Math.random()) * 0x10000).toString(16).substring(1)
    return s4() + s4() + '-' + s4() + '-' + s4() + '-' + s4() + '-' + s4() + s4() + s4();
}

describe('Add Token', function () {
  this.timeout(100000);

  beforeEach(function () {
    this.app = new Application({
      path: electronPath,
      args: [path.join(__dirname, '../..')]
    });
      return this.app.start();
  });

  afterEach(function () {
    if (this.app && this.app.isRunning()) {
        return this.app.stop();
    }
  });

  it('Adding a token and seeing that tokens get updated', async function () {
    const username = guid()
    const password = process.env.PASSWORD
    const ethAddress = process.env.ETH_ADDRESS

    // wait for sign-in / create-new-account modal
    await this.app.client.waitForExist('.jconfirm-box-container', 5000).should.eventually.equal(true);

    // choose create-new-account
    await this.app.client.execute(function () {
        $('button.create-new-account').click()
    })

    await waitAfterLoad.call(this)

    // fill values
    await this.app.client.addValue('#user_name_entry', username)
    await this.app.client.addValue('#password_entry', password)
    await this.app.client.addValue('#repeat_password_entry', password)

    // click create-new-account
    await this.app.client.waitForExist('.jconfirm-buttons>button', 5000)
    await this.app.client.execute(function () {
        $('.jconfirm-buttons>button:first').click()
    })

    await waitAfterSignup.call(this)
    
    // open dropdown menu
    await this.app.client.execute(function () {
        $('li#user-dropdown.dropdown a:first').click()
    })

    await this.app.client.pause(500)

    // make sure dropdown menu is open
    await this.app.client.waitForExist('li.dropdown.open', 5000).should.eventually.equal(true)
    
    await this.app.client.execute(function () {
        // remove all modals
        $('.jconfirm').remove()
    })
    await this.app.client.execute(function () {
        $('li#user_settings_button a:first').click()
    })

    await this.app.client.waitForExist('ul.ms-list')
    
    await this.app.client.execute(function () {
        // remove all modals
        $('.jconfirm').remove()
    })

    await this.app.client.execute(function () {
        $('body').css('overflow', 'scroll')
        $('ul.ms-list')[0].scrollIntoView()
    })
    
    // get the list of available tokens
    const tokens = await this.app.client.getText('ul.ms-list li.ms-elem-selectable')

    await this.app.client.execute(function () {
        // click first token
        $('ul.ms-list:first li.ms-elem-selectable:first').click()
    })

    // check that the <li> has been selected
    await this.app.client.waitForExist('ul.ms-list li.ms-elem-selection.ms-selected')

    await this.app.client.getText('ul.ms-list li.ms-elem-selection.ms-selected').should.eventually.equal(tokens[0])
  });

});
