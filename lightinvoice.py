#!/usr/bin/env python3
from codecs import encode as encodedata
from os import environ
from io import BytesIO
from base64 import b64encode, decodebytes
from hashlib import sha1
from time import time
from qrcode import make as makeqr
from qrcode.image.svg import SvgPathImage
from rpc_pb2_grpc import LightningStub
from rpc_pb2 import Invoice, ListInvoiceRequest
import grpc
from flask import Flask, request, url_for
app = Flask(__name__)
environ["GRPC_SSL_CIPHER_SUITES"] = "HIGH+ECDSA"


def metadata_callback(context, callback):
    maca = decodebytes(environ['MACAROON'].encode("ascii"))
    macaroon = encodedata(maca, "hex")
    callback([("macaroon", macaroon)], None)


def open_channel():
    """open a grpc channel"""
    cert = environ["TLS_CERT"].encode()
    cert_creds = grpc.ssl_channel_credentials(cert)
    auth_creds = grpc.metadata_call_credentials(metadata_callback)
    combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)
    channel = grpc.secure_channel(environ["NODE_IP"], combined_creds)
    return channel


def get_client_id():
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    # client_id = sha1(ip.encode('utf8')).hexdigest()
    return ip


class InvoiceManager:
    def __init__(self):
        self.prod_invoice = environ.get('LIGHT_ENV', 'prod') == 'prod'
        if self.prod_invoice:
            self.channel = open_channel()
            self.stub = LightningStub(self.channel)

    def list_invoices(self):
        """get an invoice for a given amt"""
        req = ListInvoiceRequest(pending_only=True, num_max_invoices=10)
        invoices = self.stub.ListInvoices(req).invoices
        return invoices

    def filter_invoices(self):
        invoices = self.list_invoices()
        t0 = time()
        invoices = [inv for inv in invoices if inv.creation_date + inv.expiry > t0 + 30]
        return invoices

    def get_invoice_prod(self, amt):
        """get an invoice for a given amt"""
        invoice_request = Invoice(value=amt, expiry=7200)
        invoice_response = self.stub.AddInvoice(invoice_request)
        invoice = invoice_response.payment_request
        return invoice

    def get_invoice_test(self):
        import uuid
        invoice = (str(uuid.uuid4()) * 8).replace('-', '')[:196]
        return invoice

    def get_invoice(self, amt):
        if self.prod_invoice:
            return self.get_invoice_prod(amt)
        else:
            return self.get_invoice_test()

    def encode_invoice(self, invoice):
        img = makeqr(invoice, image_factory=SvgPathImage)
        s = BytesIO()
        img.save(s)
        return b64encode(s.getvalue()).decode("ascii")

    def get_html(self, amt):
        if amt:
            invoice = self.get_invoice(int(amt[0]))
            encoded = self.encode_invoice(invoice)
            qr = f"data:image/svg+xml;base64,{encoded}"
            inout = f'<textarea readonly>{invoice}</textarea>'
            button_label = 'Cancel'
        else:
            qr = url_for('static', filename='bolt.svg')
            inout = '<input type="number" name="amt" min="0" max="5000000" placeholder="satoshis" pattern="[0-9]*">'
            button_label = 'Generate Invoice'

        favicon_url = url_for('static', filename='favicon.png')
        css_url = url_for('static', filename='simple.css')

        html = f'''
        <html>
        <head>
        <title>Lightning Invoice</title>
        <link rel="shortcut icon" type="image/png" href="{favicon_url}"/>
        <link rel="stylesheet" href="{css_url}">
        </head>
        <body>
        <img src="{qr}">
        <div class="centered">
        <form action="/">
        <div>{inout}</div>
        <div><button type="submit">{button_label}</button></div>
        </form>
        </div>
        <div>{get_client_id()}</div>
        </body>
        </html>'''

        return html


invoice_manager = InvoiceManager()


@app.route("/")
def hello():
    amt = request.args.get('amt', None)
    return invoice_manager.get_html(amt)


if __name__ == "__main__":
    app.run(host="0.0.0.0")
