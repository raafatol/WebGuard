
from app.services.tls_checker import check_tls
from app.services.headers_checker import check_headers
from app.services.redirect_checker import check_http_redirect
from app.services.recommendations import generate_recommendations


def analyze_website(domain):
    tls_result = check_tls(domain)
    headers_result = check_headers(domain)
    redirect_result = check_http_redirect(domain)

    recommendations = generate_recommendations(headers_result)

    return {
        "domain": domain,
        "tls": tls_result,
        "http": headers_result,
        "redirect": redirect_result,
        "recommendations": recommendations
    }
