# lightinvoice

A super simple invoice app for LND, tailored for Heroku deployment

## Setup

Using the app on Heroku requires remote access to your LND node via port 10009. 
You need to set tlsextraip in lnd.conf and recreate tls.cert to use remotely. 
See the LND configuration docs for more info.

Also note that there is not currently any limit on the number of invoices that could be created, so anyone with access to this app could maliciously create a whole lot of unused invoices. Without identifying users in some way, whether by ip address or cookies, I'm not sure there's a good way around this. I did attempt to identify ip address for a time, but I feel it's against the bitcoin ethos. Instead there is a small `sleep` to put some limit on the rate of invoice creation and prevent a DoS attack.

### Local

If you want to use on your local network:
```
export NODE_IP="x.x.x.x:10009"
export TLS_CERT=$(cat tls.cert)
export MACAROON=$(base64 invoice.macaroon)
```

You can enable test mode that doesn't query your lightning node nor create real invoices by setting env var `LIGHT_ENV` to something other than `prod`. In test mode none of the other env vars need to be set.

When running locally you can just use `python lightinvoice.py` or use gunicorn.

### Heroku

Deploy app to Heroku:

```
heroku create
git push heroku master
```

After that you should just need to set the environment variables. 

`export NODE_IP="x.x.x.x:10009"` (replace with your ip address)

`heroku config:set NODE_IP="$NODE_IP" TLS_CERT="$(cat tls.cert)" MACAROON="$(base64 invoice.macaroon)"`

To just test the app without calling your node:

`heroku config:set LIGHT_ENV=test`

To return to using your lightning node:

`heroku config:unset LIGHT_ENV`

## Appendix

You can get the cert and macaroon from your node via:
```
scp x.x.x.x:~/.lnd/data/chain/bitcoin/mainnet/invoice.macaroon .
scp x.x.x.x:~/.lnd/tls.cert .
```

## Sreenshots

### Greeting
![Initial page](screenshots/start.png)

### Example (fake) invoice
![Invoice example](screenshots/invoice.png)
