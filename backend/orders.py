import os
import re
import json
import datetime
import pytz
import requests
import tempfile
import os
from types import SimpleNamespace
from PyPDF2 import PdfMerger
from datetime import datetime
from weasyprint import HTML
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from backend.monday_utils.items import fetch_item_with_columns

MONDAY_API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjUyMjU5NjU2OSwiYWFpIjoxMSwidWlkIjo3Njc0NjQ1OSwiaWFkIjoiMjAyNS0wNi0wNVQxNTowNzowNC40MDFaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6Mjk2NTAyMjEsInJnbiI6ImFwc2UyIn0.TY4oQYraqw6fuq6I10A5Ga5JMn3LGoZv8qIQawbQlDY"
ORDERS_BOARD_ID = 2023614902   
SUPPLIER_MANIFEST_BOARD_ID = 2031231767
ORDER_LINE_ITEMS_BOARD_ID = 2028904077  
SUPPLIER_MANIFEST_BOARD_ORDER_LINE_ITEM_COLID = "board_relation_mksn5vvd"
SUPPLIER_MANIFEST_BOARD_MANIFEST_FILE_COLID = "file_mksncam"
SUPPLIER_MANIFEST_BOARD_LABEL_FILE_COLID = "file_mkv0thgs"
SUPPLIER_PRODUCT_BOARD_ID = 2026788711  
supplier_manifest_monday_record_id = 0
MONDAY_API_URL = "https://api.monday.com/v2"





def get_order_with_lineitems(order_id):
    print('enter in this orderlineitems')
    
    
    headers = {
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json"
    }

    customer_info = {
            "id": None,
            "name":"",
            "email": "",
            "phone":"",
            "address":"",
            "postal_code": "",

        }

    # 1. Fetch the order details
    order_query = f"""
    query {{
      items (ids: {order_id}) {{
        id
        name
        column_values {{
        column {{
        title
        }}
        id
        text
        value
        ... on MirrorValue {{
            display_value
            text
            value
        }}
        ... on BoardRelationValue {{
            linked_item_ids
            display_value            
        }}
        ... on FormulaValue {{
            value
            id
            display_value
            }}
        }}
      }}
    }}
    """

    order_response = requests.post(MONDAY_API_URL, headers=headers, json={"query": order_query})
    order_response.raise_for_status()
    order_data = order_response.json()
    print("order_response JSON ---->", order_data)

    order_item = order_data["data"]["items"][0]
    order_data = {
        "id": order_item["id"],
        "name": order_item["name"],
        "status": get_value("Status",order_item),
        "date": get_value("Date",order_item),
        "orderId": get_value("OrderId",order_item),
        "description": get_value("Description",order_item),
        "totalPrice": get_value("TotalPrice",order_item),
        "customerPostalCode": get_value("CustomerPostalCode",order_item),
    }
    
    print("order_data-column-value ---->", order_data)


    orderId_column_value_id = "board_relation_mks0fnmz"
    # Fetch related line items where column 'orderId' matches
    # related_lineitems = get_related_items(ORDER_LINE_ITEMS_BOARD_ID, orderId_column_value_id, 2023614909)
    # print('related_lineitems--->',related_lineitems)

    orderId_column_value_id = get_column_id(ORDER_LINE_ITEMS_BOARD_ID,"Order")
    print('orderId_column_value_id',orderId_column_value_id)

    lineitems_query = f"""
        query {{
        boards(ids: {ORDER_LINE_ITEMS_BOARD_ID}) {{
            items_page(query_params: {{rules: [ {{ column_id: "{orderId_column_value_id}", compare_value: [2023614909] }}] , operator: or}}) {{
            cursor
            items {{
                id
                name
                column_values {{
                column {{
                    title
                }}
                id
                text
                value
                ... on MirrorValue {{
                    display_value
                    text
                    value
                }}
                ... on BoardRelationValue {{
                    linked_item_ids
                    display_value            
                }}
                ... on FormulaValue {{
                    value
                    id
                    display_value
                }}
                }}
            }}
            }}
        }}
        }}
    """

    response = requests.post(MONDAY_API_URL, headers=headers, json={"query": lineitems_query})
    response.raise_for_status()
    response_json = response.json()
    print(" JSON ---->", response_json)

    boards = response_json["data"]["boards"]
    for board in boards:
        items_page = board.get("items_page", {})
        items = items_page.get("items", [])


    parsed_items = []
    for order_item in items:
        parsed_items.append({
            "id": order_item.get("id"),
            "name": order_item.get("name"),
            "orderNumber": get_value("OrderNumber", order_item),
            "product": get_value("Product", order_item),
            "product_id": get_linked_item_ids("Product", order_item),
            "productCode": get_value("lookup_mks1f46y", order_item),
            "sku": get_value("SKU", order_item),
            "quantity": get_value("Quantity", order_item),
            "unitPrice": get_value("UnitPrice", order_item),
            "listPrice": get_value("ListPrice", order_item),
            "status": get_value("Status", order_item),
            "date": get_value("Date", order_item),
            "productWeight": get_value("Product Weight", order_item),
            "customerId": get_value("CustomerId", order_item),
            "supplierId": get_linked_item_ids("Supplier", order_item),
            "courierId": get_value("courierId", order_item),
        })    
    
    print('parsed_items-lineitems=--->',parsed_items)

    # fetch the customer_columns for customer info 
    customer_id = parsed_items[0].get("customerId")
    customer_columns = fetch_item_with_columns(customer_id)
    print('customer_columns',customer_columns)
    if customer_columns:
        customer_info["id"] = customer_columns["id"]
        customer_info["name"] = customer_columns["name"]
        customer_info["email"] = get_value("Email", customer_columns)
        customer_info["phone"] = get_value("Phone", customer_columns)
        customer_info["address"] = get_value("Billing Street", customer_columns)
        customer_info["postal_code"] = get_value("PostalCode", customer_columns)

    print('customer_info----->',customer_info)

    all_product_ids = []
    for item in parsed_items:
        all_product_ids.extend(item.get("product_id", []))
    all_product_ids = [int(pid) for pid in all_product_ids]
    print('all_product_ids--->',all_product_ids)

    product_supplier_map = {}
    # supplier_items = get_related_items(SUPPLIER_PRODUCT_BOARD_ID,columnId,campare_vales)
    # print('Supplier-Items-55--->',supplier_items)

    product_column_id = get_column_id(SUPPLIER_PRODUCT_BOARD_ID,"Product")
    print('product_column_id',product_column_id)

    lineitems_query = f"""
        query {{
        boards(ids: {SUPPLIER_PRODUCT_BOARD_ID}) {{
            items_page(query_params: {{rules: [ {{ column_id: "{product_column_id}", compare_value: {all_product_ids} }}] , operator: or}}) {{
            cursor
            items {{
                id
                name
                column_values {{
                column {{
                    title
                }}
                id
                text
                value
                ... on MirrorValue {{
                    display_value
                    text
                    value
                }}
                ... on BoardRelationValue {{
                    linked_item_ids
                    display_value            
                }}
                ... on FormulaValue {{
                    value
                    id
                    display_value
                }}
                }}
            }}
            }}
        }}
        }}
    """

    response = requests.post(MONDAY_API_URL, headers=headers, json={"query": lineitems_query})
    response.raise_for_status()
    response_json = response.json()
    print(" JSON ---->", response_json)

    boards = response_json["data"]["boards"]
    for board in boards:
        items_page = board.get("items_page", {})
        items = items_page.get("items", [])

    for item in items:
        product_ids = get_linked_item_ids("Product", item)
        supplier_id = get_linked_item_ids("Supplier", item)
        supplier_name = get_value("SupplierName", item)
        supplier_adddress = get_value("Supplier Address",item)
        supplier_phone = get_value("Supplier Phone",item)
        postal_code = get_value("Postal Code", item)
        product_weight = get_value("Product Weight", item)
        rate = get_value("Rate(Per Unit)", item)
        rating = get_value("Supplier Market Rating", item)

        supplier_info = {
            "supplier_id": supplier_id[0] if supplier_id else None,
            "supplier_name": supplier_name,
            "supplier_address": supplier_adddress,
            "supplier_phone": supplier_phone,
            "postal_code": postal_code,
            "rate": rate,
            "weight": product_weight,
            "rating": rating
        }

        for pid in product_ids:
            product_supplier_map.setdefault(pid, []).append(supplier_info)

    print('product_supplier_map--->',product_supplier_map)

    for item in parsed_items:
        product_ids = item.get("product_id", [])
        suppliers = []
        for pid in product_ids:
            if pid in product_supplier_map:
                suppliers.extend(product_supplier_map[pid])
        item["suppliers"] = suppliers

    print('parsed_items_with_suppliers',parsed_items)
    return {
        "order": order_data,
        "customer": customer_info,
        "lineitems": parsed_items,
    }

def get_column_id(board_id, column_title):
    """
    Fetch the column ID dynamically from a board in Monday.com by column title.
    """
    
    query = """
    query ($boardId: [ID!]) {
        boards (ids: $boardId) {
            id
            name
            columns {
                id
                title
                type
            }
        }
    }
    """
    
    variables = {"boardId": board_id}
    
    headers = {
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        MONDAY_API_URL,
        json={"query": query, "variables": variables},
        headers=headers
    )
    
    data = response.json()
    
    if "errors" in data:
        raise Exception(f"GraphQL Error: {data['errors']}")
    
    columns = data["data"]["boards"][0]["columns"]
    
    for col in columns:
        if col["title"].lower() == column_title.lower():
            return col["id"]
    
    return None

def get_related_items(boardId , columnId, campare_vales):

    print('enter in this')
    

    headers = {
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json"
    }

    # compare_values_str = ",".join([f"\"{val}\"" for val in campare_vales])

    lineitems_query = f"""
        query {{
        boards(ids: {SUPPLIER_PRODUCT_BOARD_ID}) {{
            items_page(query_params: {{rules: [ {{ column_id: "{columnId}", compare_value: [{campare_vales}] }}] , operator: or}}) {{
            cursor
            items {{
                id
                name
                column_values {{
                column {{
                    title
                }}
                id
                text
                value
                ... on MirrorValue {{
                    display_value
                    text
                    value
                }}
                ... on BoardRelationValue {{
                    linked_item_ids
                    display_value            
                }}
                ... on FormulaValue {{
                    value
                    id
                    display_value
                }}
                }}
            }}
            }}
        }}
        }}
    """

    response = requests.post(MONDAY_API_URL, headers=headers, json={"query": lineitems_query})
    response.raise_for_status()
    response_json = response.json()
    print(" JSON ---->", response_json)

    boards = response_json["data"]["boards"]
    for board in boards:
        items_page = board.get("items_page", {})
        items = items_page.get("items", [])

    print('Suppliers items-->',items)
    return items


def get_value(title,order_item):
        for col in order_item["column_values"]:
            if col["column"]["title"] == title:
                # return col["text"]
                return col.get("text") or col.get("value") or col.get("display_value")
        return None
    
def get_linked_item_ids(title, order_item):

    for col in order_item["column_values"]:
        if col["column"]["title"] == title:
            return col.get("linked_item_ids")
    return None

def generate_label(lineitems, supplierId, supplierName, supplierAddress, courierId, courierName, customer):
    global supplier_manifest_monday_record_id

    pdf_files = []
    orders = []
    print('lineitems_get-->',lineitems)

    for item in lineitems:
        order_data = {
            "order_no": item.get("orderNumber", "N/A"),
            "awb_no": "N/A",  
            "contents": []
        }

        supplier_info = {
            "id": supplierId,
            "name": supplierName,
            "address": supplierAddress,
            "phone": ""  
        }

        customer_info = {
            "id": customer.get("id"),
            "name": customer.get("name"),
            "email": customer.get("email"),
            "postal_code": customer.get("postal_code"),
            "address": customer.get("address"),
            "phone": customer.get("phone"),
        }

        # Product info from lineitem
        product_info = {
            "id": item.get("product_id", [None])[0], 
            "name": item.get("product"),
            "sku": item.get("sku"),
            "weight": item.get("productWeight"),
            "unit_price": item.get("unitPrice"),
            "quantity": item.get("quantity"),
        }

        # Collect product content for label
        if item.get("product"):
            order_data["contents"].append(item["product"])
        if item.get("sku"):
            order_data["contents"].append(item["sku"])
        if item.get("productCode"):
            order_data["contents"].append(item["productCode"])

        order_data["contents"] = ", ".join(order_data["contents"])
        orders.append(order_data)

        # Combine everything into one payload for PDF
        label_data = {
            "order": order_data,
            "supplier": supplier_info,
            "customer": customer_info,
            "product": product_info,
            "courier": {
                "id": courierId,
                "name": courierName
            }
        }
        print("label_data_pdf --->", label_data)

        # Generate PDF for each item
        file_path = generate_label_pdf_from_html(label_data)
        pdf_files.append(file_path)

    # Merge all PDFs for this supplier-courier group
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_courier = courierName.replace(" ", "_")
    merged_file_path = f"merged_labels_{safe_courier}_{timestamp}.pdf"

    merger = PdfMerger()
    for pdf in pdf_files:
        merger.append(pdf)
    merger.write(merged_file_path)
    merger.close()

    # Upload final merged label file
    upload_file_to_supplier_manifest_column(
        supplier_manifest_monday_record_id,
        merged_file_path,
        SUPPLIER_MANIFEST_BOARD_LABEL_FILE_COLID
    )

    # Cleanup temporary PDFs
    for pdf in pdf_files:
        try:
            os.remove(pdf)
        except Exception as e:
            print("Error deleting file:", pdf, e)

    return orders



# this function handles the manifest generation for orders
def generate_manifest(order_line_items, supplierId, supplierName, supplierAddress, courierId, courierName, customer):
    global supplier_manifest_monday_record_id
    orders = []

    print("courier for pdf -->", courierName)

    for item in order_line_items:
        order_data = {
            "order_no": item.get("orderNumber", "N/A"),
            "awb_no": "N/A",   # Can be filled later if generated
            "contents": [],
        }

        # Collect product details
        if item.get("product"):
            order_data["contents"].append(item["product"])
        if item.get("productCode"):
            order_data["contents"].append(item["productCode"])
        if item.get("sku"):
            order_data["contents"].append(item["sku"])

        order_data["contents"] = ", ".join(order_data["contents"])
        orders.append(order_data)

    # Log supplier/courier info
    print("supplierName for pdf:", supplierName)
    print("supplierId for pdf:", supplierId)
    print("supplierAddress for pdf:", supplierAddress)
    print("courierName for pdf:", courierName)

    # --- Create supplier manifest record ---
    supplier_manifest_mondayrecord = create_supplier_manifest_record(
        orders, supplierName, supplierId, courierName
    )
    supplier_manifest_monday_record_id = supplier_manifest_mondayrecord["id"]
    print("supplier_manifest_monday_record_id --->", supplier_manifest_monday_record_id)

    # --- Generate PDF ---
    file_path = generate_manifest_pdf_from_html(
        orders, supplierName, supplierAddress, supplierPhone="", courierName=courierName
    )

    # --- Upload Manifest PDF to Monday.com ---
    upload_file_to_supplier_manifest_column(
        supplier_manifest_monday_record_id,
        file_path,
        SUPPLIER_MANIFEST_BOARD_MANIFEST_FILE_COLID
    )

    # --- Update status for each line item ---
    for item in order_line_items:
        item_id = item.get("id")
        if item_id:
            update_order_line_item(int(item_id),
            "Manifest Generated",   
            supplierId,
            supplierName,
            courierId,
            courierName,
            ORDER_LINE_ITEMS_BOARD_ID)

    return {
        "supplierName": supplierName,
        "supplierId": supplierId,
        "courierName": courierName,
        "courierId": courierId,
        "totalOrders": len(orders),
        "orders": orders
    }


def update_order_line_item(item_id, status, supplier_id, supplier_name, courier_id, courier_name, board_id):
    print('enter in this update order line item')
    print('item_id', item_id)
    print('status', status)
    print('supplier_id', supplier_id)
    print('supplier_name', supplier_name)
    print('courier_id', courier_id)
    print('courier_name', courier_name)
    print('board_id', board_id)

    mutation = """
        mutation ($itemId: ID!, $boardId: ID!, $columnValues: JSON!) {
          change_multiple_column_values (
            item_id: $itemId,
            board_id: $boardId,
            column_values: $columnValues
          ) {
            id
          }
        }
    """

    # Build column values as dict
    column_values = {
        "status": {"label": status},
        "board_relation_mks3arpf": {"item_ids": [str(supplier_id)]},  # relation field
        "text_mkw4jp1r": str(courier_id),  # text field
        "text_mkw41y6y": courier_name      # text field
    }

    variables = {
        "itemId": str(item_id),
        "boardId": str(board_id),
        "columnValues": json.dumps(column_values)  # must be JSON string
    }

    response = requests.post(
        "https://api.monday.com/v2",
        headers={"Authorization": MONDAY_API_KEY},
        json={"query": mutation, "variables": variables}
    )

    return response.json()


def upload_file_to_supplier_manifest_column(item_id, file_path, column_id):

    url = "https://api.monday.com/v2/file"
    headers = {
        "Authorization": MONDAY_API_KEY,
        "API-version": "2024-04"
    }
    query = """
    mutation add_file($file: File!, $itemId: ID!, $columnId: String!) {
      add_file_to_column (item_id: $itemId, column_id: $columnId, file: $file) {
        id
      }
    }
    """

    payload = {
        "query": query,
        "variables": json.dumps({
            "file": None,
            "itemId": str(item_id),
            "columnId": column_id
        }),
        "map": '{"pdf": ["variables.file"]}'
    }

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    files = {
        'pdf': (os.path.basename(file_path), open(file_path, 'rb'), 'application/pdf')
    }

    print("Uploading PDF...",flush=True)
    print(f"→ item_id: {item_id}",flush=True)
    print(f"→ column_id: {column_id}",flush=True)
    print(f"→ file_path: {file_path}",flush=True)
    print(f"→ file exists: {os.path.exists(file_path)}",flush=True)
    print(f"→ file size: {os.path.getsize(file_path)}",flush=True)

    response = requests.post(url, headers=headers, data=payload, files=files)

    try:
        resp_json = response.json()
        print("Response-JSON:", json.dumps(resp_json, indent=2),flush=True)
        if "errors" in resp_json:
            print("GraphQL-Errors:", resp_json["errors"],flush=True)
        else:
            print("PDF uploaded successfully.",flush=True)
    except Exception as e:
        print("Failed to parse response:", str(e),flush=True)
        print("Raw response:", response.text,flush=True)

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

# this function generate the pdf using html
def generate_manifest_pdf_from_html(orders, supplierName, supplierAddress,supplierPhone, courierName):
    print('generate_manifest_pdf_from_html',flush=True)
    # current_date = datetime.now().strftime("%B %d")
    # current_datetime = datetime.now().strftime("%B %d, %Y %I:%M %p")

    ist = pytz.timezone('Asia/Kolkata')
    ist_now = datetime.now(ist)
    current_date = ist_now.strftime("%B %d")
    current_datetime = ist_now.strftime("%B %d, %Y %I:%M %p")

    filename = f"{supplierName}_{courierName}_({current_date})"
    file_name = sanitize_filename(filename) + ".pdf"

    output_dir = tempfile.gettempdir()
    file_path = os.path.join(output_dir, file_name)

    print("PDF file path to be written:", file_path)

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("manifest-pdf.html")

    html_out = template.render(
        orders=orders,
        total=len(orders),
        supplierName=supplierName,
        courierName=courierName,
        current_datetime=current_datetime,
        supplierAddress = supplierAddress,
        supplierPhone = supplierPhone
    )

    HTML(string=html_out).write_pdf(file_path)
    print("Manifest PDF generated at:", file_path)

    return file_path

def generate_label_pdf_from_html(label_data):
    ist = pytz.timezone('Asia/Kolkata')
    ist_now = datetime.now(ist)
    current_date = ist_now.strftime("%B %d")
    current_datetime = ist_now.strftime("%B %d, %Y %I:%M %p")

    supplier = label_data["supplier"]
    courier = label_data["courier"]
    orders = label_data["order"] if isinstance(label_data["order"], list) else [label_data["order"]]
    product = label_data["product"]

    filename = f"{supplier['name']}_{courier}_{label_data['product']['id']}_{current_date}"
    file_name = sanitize_filename(filename) + ".pdf"

    output_dir = tempfile.gettempdir()
    file_path = os.path.join(output_dir, file_name)

    print("PDF file path to be written:", file_path)

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("label-pdf.html")

    html_out = template.render(
        orders=orders,
        total=len(orders),
        supplierName=supplier["name"],
        courierName=courier,
        current_datetime=current_datetime,
        supplierAddress=supplier["address"],
        supplierPhone=supplier["phone"],
        customer=dict_to_obj(label_data.get("customer", {})),
        product=dict_to_obj(label_data.get("product", {}))
    )

    HTML(string=html_out).write_pdf(file_path)
    print("Label PDF generated at:", file_path)

    return file_path


# this function create new supplier manifest record on monday
def create_supplier_manifest_record(orders, supplier_name, supplier_item_id, courierName):

    # Combine all order numbers into a comma-separated string
    order_nos = ", ".join(order.get("order_no", "") for order in orders)

    board_id = 2031231767
    column_id = "text_mktb6jtd"
    supplier_column_id = "board_relation_mktqzxcn"

    # current_time = datetime.now().strftime("%B %d, %Y %I:%M %p")
    current_date = datetime.now().strftime("%B %d")

    item_name = f"{supplier_name}_{courierName}_({current_date})" if supplier_name else f"Manifest Record ({current_date})"

    # column values
    column_values = {
        column_id: order_nos,
        supplier_column_id: {
            "linkedPulseIds": [{"linkedPulseId": supplier_item_id}]
        }
    }

    # Escape for GraphQL
    column_values_str = json.dumps(column_values).replace('"', '\\"')

    mutation = f'''
    mutation {{
      create_item(
        board_id: {board_id},
        item_name: "{item_name}",
        column_values: "{column_values_str}"
      ) {{
        id
      }}
    }}
    '''

    response = requests.post(
        "https://api.monday.com/v2",
        headers={
            "Authorization": MONDAY_API_KEY,
            "Content-Type": "application/json"
        },
        json={"query": mutation}
    )

    data = response.json()
    print("Response from Monday:", data)

    item_id = data.get("data", {}).get("create_item", {}).get("id")
    success = item_id is not None
    errors = data.get("errors", []) if not success else []

    return {"success": success, "id": item_id, "errors": errors}


def generate_token(email, password):

    URL = "https://apiv2.shiprocket.in/v1/external/auth/login"
    payload = json.dumps({
        "email": email,
        "password": password
    })
    headers = {
    'Content-Type': 'application/json'
    }

    status_code = None
    error = None
    success = False
    token = None
    try:
        response = requests.post(URL, headers=headers, data=payload)
        response.raise_for_status()
        success = True
        response_json = response.json()
        status_code = response.status_code
        token = response_json.get("token", None) if response_json is not None else None
    except requests.exceptions.Timeout as te:
        error = f'Timeout exception {te}'
    except requests.exceptions.TooManyRedirects as re:
        error = f'Too many redirects {re} '
    except requests.exceptions.RequestException as e:
        error = f'HTTP Exception {e}'
        status_code = response.status_code
    except Exception as e:
        error = f'Exception occurred {e}'
    return {
        'success': success,
        'status_code': status_code,
        'token': token,
        'error': error
    }


def check_courier_serviceability(pickup_pincode, delivery_pincode, weight, cod):
    print('enter check courier sevice ')

    print('pickup_pincode',pickup_pincode)
    print('delivery_pincode',delivery_pincode)
    print('weight',weight)
    print('cod',cod)

    api_token = generate_token("emailfortrialds1@gmail.com", "AG%@q6!tX4l55J%Z")
    print('api_token-0------->' + api_token["token"], flush=True)

    url = (
        f"https://apiv2.shiprocket.in/v1/external/courier/serviceability/"
        f"?pickup_postcode={pickup_pincode}&delivery_postcode={delivery_pincode}&weight={weight}&cod={cod}"
    )
    headers = {
        "Authorization": f"Bearer {api_token['token']}"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def dict_to_obj(d):
    return SimpleNamespace(**d)
