# Rotkehlchen

Rotkehlchen is an asset management and accounting application specializing in Crypto assets and aims to also help with tax reporting. It is integrated with multiple exchanges and more will come soon.


## Installation

For now only Linux is supported and only installation from source. This will change soon and both other platforms will be supported but also easier to install methods will be provided

Rotkehlchen needs  Python3 in order to function.

### Linux

Make sure you have [node.js](https://nodejs.org/en/) and [npm](https://www.npmjs.com/). If you don't use your linux distro's package manager to get them.

Get [zeromq](http://zeromq.org/) using the package manager of your distro. For example here is the package in [Archlinux](https://www.archlinux.org/packages/community/x86_64/zeromq/) and in [Ubuntu](https://packages.ubuntu.com/source/trusty/libs/zeromq).

Also get [sqlcipher](https://www.zetetic.net/sqlcipher/):

- If you're running Archlinux you can install the [package](https://www.archlinux.org/packages/community/x86_64/sqlcipher/) with the package manager of your distro.

- If you're running Ubuntu you will need to install [libsqlcipher-dev](https://packages.ubuntu.com/trusty/libdevel/libsqlcipher-dev) with the package manager of your distro instead 

Install electron and any other npm dependencies by:

```
npm install --runtime=electron --target=1.8.4
```

Create a new [virtual environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/) to install all the python dependencies. If you don't have `mkvirtualenv` then check how to get it depending on your distribution. [Here](http://exponential.io/blog/2015/02/10/install-virtualenv-and-virtualenvwrapper-on-ubuntu/) is a guide for Ubuntu and [here](https://wiki.archlinux.org/index.php/Python/Virtual_environment) is one for ArchLinux.

```
mkvirtualenv rotkehlchen
```

Then install all the python requirements by doing:

```
pip install -r requirements.txt
```


Now to start the application you need to type `npm start`.

### OSX

NOTE: While possible, the installation on OSX is still unsupported.

The &lt;tldr&gt; version is:
- install sqlcipher
- use a virtual env with python 3.6.x
- make sure pip installed everything it says it installed
- get your node under control with nvm, i tested 8.9

The following recipe has been tested using [Anaconda](https://conda.io). [VirtualEnv](https://virtualenv.pypa.io) works as well, refer to the documentations of those projects to install and use them.

Rotkehlchen uses an encrypted database called [SQLCipher](https://www.zetetic.net/sqlcipher/). Before we can proceed, we need to install it. Homebrew makes it simple:

	$ brew update && brew install sqlcipher

If you wish to use Conda, use the following commands:

	$ brew cask install caskroom/cask/anaconda
	$ echo "export PATH=$PATH:/usr/local/anaconda3/bin" >> ~/.bash_profile
	$ echo ". /usr/local/anaconda3/etc/profile.d/conda.sh" >> ~/.bash_profile
	$ source ~/.bash_profile
	$ conda create python=3.6 --name rotkehlchen
	$ conda activate rotkehlchen

Before using `pip`, let´s ensure we have the latest version:

	$ pip install --upgrade pip

Install all the requirements:

	$ sudo pip install -r requirements.txt

Rotkehlchen uses electron, we need to install it:

	$ npm install --runtime=electron --target=1.8.4

Almost there, we can now install all the NodeJS dependencies. Using a recent NodeJS version such as 8.9.x, it should be smooth

	$ npm install

You now deserved to start Rotkehlchen:

	$ npm start


## Love it? Want to help?


### Contribute

It's an open-source project so help is really appreciated. Open issues, pull requests to help with development, be active in Github and above all be nice.


### Get Premium -- Coming Soon

Buy a premium subscription to the software and help us with the development while at the same time enjoying all the cool neat features coming to premium subscribers.

### Donate

Don't want or can't afform premium? Still wanna help? We also accept donations.

- Donate ETH or ERC20 tokens to this address: [0x9531c059098e3d194ff87febb587ab07b30b1306](https://etherscan.io/address/0x9531c059098e3d194ff87febb587ab07b30b1306)

- Donate BTC to: 1PfvkW8MC7Ns2y8zn6CE2P2t5f19KF8XiW

