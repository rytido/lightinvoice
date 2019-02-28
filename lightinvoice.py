#!/usr/bin/env python3
import codecs
from os import environ
from io import BytesIO
from base64 import b64encode, decodebytes
from qrcode import make as makeqr
from qrcode.image.svg import SvgPathImage
import rpc_pb2 as ln
import rpc_pb2_grpc as lnrpc
import grpc
from flask import Flask, request, url_for
app = Flask(__name__)
environ["GRPC_SSL_CIPHER_SUITES"] = "HIGH+ECDSA"


def metadata_callback(context, callback):
    # maca = open("invoice.macaroon", "rb").read()
    maca = decodebytes(environ['MACAROON'].encode("ascii"))
    macaroon = codecs.encode(maca, "hex")
    callback([("macaroon", macaroon)], None)


def open_channel():
    """open a grpc channel"""
    # cert = open("tls.cert", "rb").read()
    cert = environ["TLS_CERT"].encode()
    cert_creds = grpc.ssl_channel_credentials(cert)
    auth_creds = grpc.metadata_call_credentials(metadata_callback)
    combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)
    channel = grpc.secure_channel(environ["NODE_IP"], combined_creds)
    return channel


def get_invoice(amt):
    """get an invoice for a given amt"""
    channel = open_channel()
    stub = lnrpc.LightningStub(channel)
    invoice_request = ln.Invoice(value=amt, expiry=7200)
    invoice_response = stub.AddInvoice(invoice_request)
    invoice = invoice_response.payment_request
    return invoice


def get_invoice_test(amt):
    import uuid
    invoice = (str(uuid.uuid4()) * 8).replace('-', '')[:196]
    return invoice


def encode_invoice(invoice):
    img = makeqr(invoice, image_factory=SvgPathImage)
    s = BytesIO()
    img.save(s)
    return b64encode(s.getvalue()).decode("ascii")


def get_html(amt):
    if amt is None:
        qr = url_for('static', filename='bolt.svg')
        inout = f'<input type="number" name="amt" min="0" max="5000000" placeholder="satoshis" pattern="[0-9]*">'
        button_label = 'Generate Invoice'
    else:
        invoice = get_invoice(int(amt[0]))
        encoded = encode_invoice(invoice)
        qr = f"data:image/svg+xml;base64,{encoded}"
        inout = f'<textarea readonly>{invoice}</textarea>'
        button_label = 'Cancel'

    html = f'''
    <html>
    <head>
    <title>Lightning Invoice</title>
    <link rel="shortcut icon" type="image/png" href="{url_for('static', filename='favicon.png')}"/>
    <link rel="stylesheet" href="{url_for('static', filename='simple.css')}">
    </head>
    <body>
    <img src="{qr}">
    <div class="centered">
    <form action="/">
    <div>{inout}</div>
    <div><button type="submit">{button_label}</button></div>
    </form>
    </div>
    </body>
    </html>'''

    return html


@app.route("/")
def hello():
    amt = request.args.get('amt', None)
    return get_html(amt)


if __name__ == "__main__":
    app.run(host="0.0.0.0")

