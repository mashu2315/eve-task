with open("README.md", "r") as f:
    content = f.read()

pagination_section = """
## Pagination

List endpoints (like GET centres, tests, and bookings) now return a paginated response using `page` and `size` parameters. 

Example response:
```json
{
  "items": [...],
  "page": 1,
  "size": 10,
  "total_pages": 5,
  "total_items": 50
}
```

"""

if "## Pagination" not in content:
    content = content.replace("## Rate Limiting", pagination_section + "## Rate Limiting")

with open("README.md", "w") as f:
    f.write(content)
