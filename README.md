# Setup

## Env Vars

If you want to test locally using env vars:
```
export NODE_IP="x.x.x.x:10009"
export TLS_CERT=$(cat tls.cert)
export MACAROON=$(base64 invoice.macaroon)
```

For Heroku, go to app settings, then Config Vars.

xclip is convenient for putting cert in clipboard:
`sudo apt install xlcip`

Key: `NODE_IP`
Value: `x.x.x.x:10009` (replace with your IP address)

Key: `TLS_CERT`

Then run: `cat tls.cert | xclip -i -select clipboard`

This will put the cert in your clipboard. Paste into Value and click Add.

Key: `MACAROON`

`base64 invoice.macaroon | xclip -i -select clipboard`

## Deploy

`git push heroku master`

Check logs: `/snap/bin/heroku logs`

## Appendix

You can get the cert and macaroon from your node via:
```
scp x.x.x.x:~/.lnd/data/chain/bitcoin/mainnet/invoice.macaroon .
scp x.x.x.x:~/.lnd/tls.cert .
```

