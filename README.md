# Pretix Checkin List Export Plugin for NETWAYS

This plugin adds a custom checkin list export for NETWAYS hosted events and conferences
using <a href="https://pretix.eu/about/en/"><img src="https://github.com/NETWAYS/pretix-invoice-net/blob/master/res/logo.png" height="25"></a>.

## Installation

https://pypi.python.org/pypi/pretix-checkinlist-net

### pip

```
pip install pretix-checkinlist-net
```

### Manual installation

```
cp -rv pretix-checkinlist-net/* /usr/src/pretix-checkinlist-net/
pip3 install /usr/src/pretix-checkinlist-net/
```

## Configuration

Navigate into the admin control panel and choose your event.

`Settings > Plugins` and enable the plugin.

`Orders > Export > Check-in list (CSV) for NETWAYS`.

## Documentation

https://docs.pretix.eu/en/latest/development/api/plugins.html

Checkin List Export is inspired by [upstream](https://github.com/pretix/pretix/blob/master/src/pretix/plugins/checkinlists/exporters.py).

## Development setup

1. Make sure that you have a working [pretix development setup](https://docs.pretix.eu/en/latest/development/setup.html).
2. Clone this repository, eg to ``local/pretix-checkinlist-net``.
3. Activate the virtual environment you use for pretix development.
4. Execute ``python setup.py develop`` within this directory to register this application with pretix's plugin registry.
5. Execute ``make`` within this directory to compile translations.
6. Restart your local pretix server. You can now use the plugin from this repository for your events by enabling it in
   the 'plugins' tab in the settings.


# Thanks

Raphael Michel for Pretix and the initial checkin list export code, which is adopted in this custom renderer plugin.

# License

Copyright 2018 NETWAYS GmbH <support@netways.de>
Copyright 2018 Raphael Michel <mail@raphaelmichel.de>

The code in this repository is published under the terms of the Apache License.
See the LICENSE file for the complete license text.
