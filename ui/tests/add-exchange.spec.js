// Nice overview for electron tests with the chai.should model:
// https://dzone.com/articles/write-automated-tests-for-electron-with-spectron-m

const {
    path, chai, Application, electronPath, waitAfterLoad, waitAfterSignup
} = require('./utils/setup')

const guid = () => {
    const s4 = () => Math.floor((1 + Math.random()) * 0x10000).toString(16).substring(1)
    return s4() + s4() + '-' + s4() + '-' + s4() + '-' + s4() + '-' + s4() + s4() + s4();
}

describe('User Settings: Exchange', function () {
  this.timeout(60000);

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

  it('Add an exchange and see that the API key is succesfully accepted', async function () {
    const username = guid()
    const password = process.env.PASSWORD
    const bittrex = {
        key: process.env.BITTREX_API_KEY,
        secret: process.env.BITTREX_API_SECRET
    }

    // wait for sign-in / create-new-account modal
    await this.app.client.waitForExist('.jconfirm-box-container', 5000).should.eventually.equal(true);

    // choose create-new-account
    await this.app.client.click('button.create-new-account')

    await waitAfterLoad.call(this)

    // fill values
    await this.app.client.addValue('#user_name_entry', username)
    await this.app.client.addValue('#password_entry', password)
    await this.app.client.addValue('#repeat_password_entry', password)

    // click create-new-account
    await this.app.client.waitForExist('.jconfirm-buttons>button', 5000)
    await this.app.client.click('.jconfirm-buttons>button')

    await waitAfterSignup.call(this)
    
    // open dropdown menu
    await this.app.client.click('li#user-dropdown.dropdown')

    // make sure dropdown menu is open
    await this.app.client.waitForExist('li.dropdown.open', 5000).should.eventually.equal(true)
    
    await this.app.client.execute(function () {
        // remove all modals
        $('.jconfirm').remove()
    })
    await this.app.client.click('li#user_settings_button')

    await this.app.client.execute(function () {
        $('body').css('overflow', 'scroll')
        $('#fiat_type_entry')[0].scrollIntoView()
    })
    await this.app.client.waitForExist('#fiat_balances_table td.dataTables_empty')

    await this.app.client.pause(1000)

    await this.app.client.execute(function () {
        // remove all modals
        $('.jconfirm').remove()
        $('#setup_exchange').val('bittrex')
    })

    // register the bittrex API key and secret

    await this.app.client.addValue('#api_key_entry', bittrex.key)
    await this.app.client.addValue('#api_secret_entry', bittrex.secret)
    await this.app.client.click('#setup_exchange_button')

    // try {
    //     // make sure the BITTREX API KEY and SECRET has not already been registered
    //     await this.app.client.waitForExist('.jconfirm').should.eventually.equal(false)
    // }
    // catch (err) {
    //     throw new Error(await this.app.client.getText('.jconfirm-content'))
    // }

    await this.app.client.waitForExist('#exchange_panel_body .form-group.input-group.has-success', 28000)

    await this.app.client.getValue('#api_key_entry').should.eventually.equal('bittrex API Key is already registered')

    await this.app.client.getValue('#api_secret_entry').should.eventually.equal('bittrex API Secret is already registered')

    // remove the bittrex registration, so we can test again

    await this.app.client.click('#setup_exchange_button')

    await this.app.client.execute(function () {
        // confirm remove
        $('.jconfirm-buttons button.btn.btn-default:first').click()
    })
  });

});
