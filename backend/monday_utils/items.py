
import requests
MONDAY_API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjUyMjU5NjU2OSwiYWFpIjoxMSwidWlkIjo3Njc0NjQ1OSwiaWFkIjoiMjAyNS0wNi0wNVQxNTowNzowNC40MDFaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6Mjk2NTAyMjEsInJnbiI6ImFwc2UyIn0.TY4oQYraqw6fuq6I10A5Ga5JMn3LGoZv8qIQawbQlDY"

MONDAY_API_URL = "https://api.monday.com/v2"


def fetch_item_with_columns(item_id):

    headers = { 
    "Authorization": MONDAY_API_KEY,
    "Content-Type": "application/json"
    }

    query = f"""
    query {{
      items(ids: {item_id}) {{
        id
        name
        column_values {{
          id
          text
          value
          type
          column {{
            title
          }}
        }}
      }}
    }}
    """

    response = requests.post(MONDAY_API_URL, json={"query": query}, headers=headers)
    data = response.json()

    if "errors" in data:
        print("Error:", data["errors"])
        return None

    items = data["data"]["items"]
    if not items:
        print(f"No item found with id {item_id}")
        return None

    return items[0]


