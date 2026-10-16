from app.services.tls_checker import check_tls

domain = "www.google.com"

result = check_tls(domain)

for key, value in result.items():
    print(f"{key}: {value}")