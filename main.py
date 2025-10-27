from flask import Flask, request, jsonify, render_template, send_from_directory
import os
from backend.orders import get_order_with_lineitems
from flask_cors import CORS
from backend.orders import generate_manifest
from backend.orders import generate_label
from backend.orders import check_courier_serviceability

import socket
import requests.adapters
from urllib3.util.connection import create_connection

# Bypass DNS issues
def patched_create_connection(address, *args, **kwargs):
    host, port = address
    if host == 'api.monday.com':
        host = '104.18.24.105'  # Monday.com IP
    elif host == 'apiv2.shiprocket.in':
        host = '104.21.22.166'  # Shiprocket IP
    return create_connection((host, port), *args, **kwargs)

# Apply the patch
import urllib3.util.connection
urllib3.util.connection.create_connection = patched_create_connection

# Add these to your main.py
app = Flask(__name__, static_folder='out', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})


@app.route('/')
def serve_react_app():
    return send_from_directory('out', 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory('out', path)


MONDAY_API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjUyMjU5NjU2OSwiYWFpIjoxMSwidWlkIjo3Njc0NjQ1OSwiaWFkIjoiMjAyNS0wNi0wNVQxNTowNzowNC40MDFaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6Mjk2NTAyMjEsInJnbiI6ImFwc2UyIn0.TY4oQYraqw6fuq6I10A5Ga5JMn3LGoZv8qIQawbQlDY"

# app = Flask(__name__)
# CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/test", methods=["GET"])
def test():
    return jsonify({"message": "Server is working!", "status": "success"})

@app.route("/order", methods=["GET"])
def order_details():
    print('hello world',flush=True)
    order_id = 2023614909
    data = get_order_with_lineitems(order_id)
    print('data--->',data,flush=True)
    return jsonify(data)

@app.route("/get-couriers", methods=["POST"])
def get_couriers():
    print('enter get couriers')
    data = request.json
    print('data for courier-->',data)
    supplier_postal = data["supplier_postalcode"]
    print('data for courier supplier_postal-->',supplier_postal)
    customer_postal = data["customer_postalcode"]
    print('data for courier customer_postal-->',customer_postal)
    weight = data["weight"]
    cod = data.get("cod", 0)

    try:
        couriers = check_courier_serviceability(
            pickup_pincode=supplier_postal,
            delivery_pincode=customer_postal,
            weight=weight,
            cod=cod
        )
        return jsonify({"couriers": couriers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route("/generate-manifest", methods=["POST"])
def generate_manifests():
    try:
        data = request.get_json()
        print("Data received for manifest =>", data, flush=True)

        # Required keys
        supplierId = data.get("supplierId")
        supplierName = data.get("supplierName")
        supplierAddress = data.get("supplierAddress")
        courierId = data.get("courierId")
        courierName = data.get("courierName")
        customer = data.get("customer")
        lineitems = data.get("lineitems", [])

        if not supplierId or not supplierName or not courierId:
            return jsonify({"error": "Missing required supplier/courier details"}), 400

        print(f"Supplier: {supplierName}, Courier: {courierName}", flush=True)

        results = generate_manifest(
            lineitems,
            supplierId,
            supplierName,
            supplierAddress,
            courierId,
            courierName,
            customer
        )

        return jsonify(results)
    except Exception as e:
        print("Exception occurred:", e, flush=True)
        return jsonify({"error": str(e)}), 500


@app.route("/generate-label", methods=["POST"])
def generate_labels():
    try:
        data = request.get_json()
        print("Data received for label=>", data, flush=True)

        # Validate payload
        if not data or "lineitems" not in data:
            return jsonify({"error": "Missing 'lineitems' key"}), 400

        supplierId = data.get("supplierId")
        supplierName = data.get("supplierName")
        supplierAddress = data.get("supplierAddress")
        courierId = data.get("courierId")
        courierName = data.get("courierName")
        customer = data.get("customer", {})
        lineitems = data.get("lineitems", [])

        if not supplierId or not courierId or not lineitems:
            return jsonify({"error": "Missing required supplier/courier/lineitems info"}), 400

        # Log one lineitem for debugging
        print("First lineitem =>", lineitems[0], flush=True)
        print(f"Supplier: {supplierName}, Courier: {courierName}", flush=True)
        print('lineitems_for_label',lineitems)

        # Call updated label generation function
        results = generate_label(
            lineitems,
            supplierId,
            supplierName,
            supplierAddress,
            courierId,
            courierName,
            customer
        )
        # print('results',results)
        return jsonify(results)
    except Exception as e:
        print("Exception occurred:", e, flush=True)
        return jsonify({"error": str(e)}), 500



if __name__  == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
    # app.run(debug=True, port=8000)
