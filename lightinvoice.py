#!/usr/bin/env python3
from codecs import encode as encodedata
from os import environ
from io import BytesIO
from base64 import b64encode, decodebytes
from time import sleep
from qrcode import make as makeqr
from qrcode.image.svg import SvgPathImage
from rpc_pb2_grpc import LightningStub
from rpc_pb2 import Invoice, ListInvoiceRequest, InvoiceSubscription
import grpc
from flask import Flask, request, url_for, Response
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


class InvoiceManager:
    def __init__(self):
        self.prod_invoice = environ.get('LIGHT_ENV', 'prod') == 'prod'
        if self.prod_invoice:
            self.channel = open_channel()
            self.stub = LightningStub(self.channel)

    def list_invoices(self):
        """get an invoice for a given amt"""
        req = ListInvoiceRequest(pending_only=True, num_max_invoices=10, reversed=True)
        invoices = self.stub.ListInvoices(req).invoices
        return invoices

    def find_invoice(self, amt):
        """find an invoice"""
        from time import time
        invoices = self.list_invoices()
        t0 = time()
        for invoice in invoices:
            if invoice.creation_date + invoice.expiry > t0 + 30:
                if invoice.value == amt:
                    return invoice.payment_request
        return None

    def make_invoice_prod(self, amt):
        """make an invoice for a given amt
        was setting description_hash=self.client_id,
        but apparently this errs for user when lacking a description
        """
        invoice_request = Invoice(value=amt, expiry=3600)
        invoice_response = self.stub.AddInvoice(invoice_request)
        invoice = invoice_response.payment_request
        return invoice

    def make_invoice_test(self):
        return "This is a lame test invoice"

    def set_invoice(self, amt):
        if self.prod_invoice:
            payreq = self.find_invoice(amt)
            if payreq:
                self.payreq = payreq
            else:
                self.payreq = self.make_invoice_prod(amt)
        else:
            self.payreq = self.make_invoice_test()

    def encode_invoice(self, invoice):
        img = makeqr(invoice, image_factory=SvgPathImage)
        bytes_io = BytesIO()
        img.save(bytes_io)
        return b64encode(bytes_io.getvalue()).decode("ascii")

    def invoice_settled(self):
        for invoice in self.stub.SubscribeInvoices(InvoiceSubscription()):
            if invoice.settled and invoice.payment_request == self.payreq:
                return True

    def get_html(self, amt):
        if amt:
            self.set_invoice(int(amt[0]))
            encoded = self.encode_invoice(self.payreq)
            qr = f"data:image/svg+xml;base64,{encoded}"
            inout = f'<textarea readonly>{self.payreq}</textarea>'
            button_label = 'Cancel'
        else:
            qr = url_for('static', filename='bolt.svg')
            inout = '<input type="number" name="amt" min="0" max="5000000" placeholder="satoshis" pattern="[0-9]*">'
            button_label = 'Generate Invoice'

        favicon_url = url_for('static', filename='favicon.png')
        css_url = url_for('static', filename='simple.css')
        js_url = url_for('static', filename='sse.js')

        html = f'''
        <html>
        <head>
        <title>Lightning Invoice</title>
        <link rel="shortcut icon" type="image/png" href="{favicon_url}"/>
        <link rel="stylesheet" href="{css_url}">
        <script src="{js_url}"></script>
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


invoice_manager = InvoiceManager()


@app.route("/")
def hello():
    amt = request.args.get('amt', None)
    if amt:
        sleep(1)  # a slight throttle to mitigate attacks
    return invoice_manager.get_html(amt)


@app.route("/success")
def success():
    def success_stream():
        if invoice_manager.invoice_settled():
            return f"data: success\n\n"

    return Response(success_stream(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(host="0.0.0.0")
