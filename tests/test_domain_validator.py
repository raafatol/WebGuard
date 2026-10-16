
import pytest

from app.services.domain_validator import validate_domain


def test_dominio_valido():
    resultado = validate_domain("example.com")
    assert resultado == "example.com"


def test_dominio_con_mayusculas_y_espacios():
    resultado = validate_domain("  WWW.GOOGLE.COM  ")
    assert resultado == "www.google.com"


def test_dominio_con_formato_invalido():
    with pytest.raises(ValueError, match="Formato de dominio no válido"):
        validate_domain("dominio..com")


def test_dominio_no_autorizado():
    with pytest.raises(ValueError, match="Dominio no autorizado"):
        validate_domain("openai.com")


def test_dominio_con_guion_inicial():
    with pytest.raises(ValueError, match="Formato de dominio no válido"):
        validate_domain("-example.com")


def test_dominio_sin_extension():
    with pytest.raises(ValueError, match="Formato de dominio no válido"):
        validate_domain("localhost")
