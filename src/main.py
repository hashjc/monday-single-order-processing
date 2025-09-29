from flask import Flask, request, jsonify, render_template
import os
from orders import get_order_with_lineitems
from flask_cors import CORS
from orders import generate_manifest
from orders import generate_label
from orders import check_courier_serviceability
MONDAY_API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjUyMjU5NjU2OSwiYWFpIjoxMSwidWlkIjo3Njc0NjQ1OSwiaWFkIjoiMjAyNS0wNi0wNVQxNTowNzowNC40MDFaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6Mjk2NTAyMjEsInJnbiI6ImFwc2UyIn0.TY4oQYraqw6fuq6I10A5Ga5JMn3LGoZv8qIQawbQlDY"

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})



@app.route("/order", methods=["GET"])
def order_details():
    order_id = 2023614909
    data = get_order_with_lineitems(order_id)
    print('data--->',data)
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

@app.route("/api/users", methods=['GET'])
def users():
    return jsonify(
        {
            "users":[
                'john',
                'mike',
                'maddy',
                'don'
            ]
        }
    )


if __name__  == '__main__':
    app.run(debug=True, port=8000)
