# store/services/shipping.py

import os
import requests
import logging
from decimal import Decimal
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class ShippingError(Exception):
    """Excepción base para errores del servicio de envío."""
    pass


class AndreaniClient:
    """
    Cliente para el API de Andreani.

    Attributes:
        base_url (str): URL base de la API.
        api_key (str): Token o llave de autenticación.
        timeout (int): Timeout en segundos para las peticiones.
        proxies (Optional[Dict[str,str]]): Configuración de proxy si se necesita.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 5,
        proxies: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Args:
            api_key: Tu token de Andreani, tomado de la variable de entorno ANDREANI_API_KEY.
            base_url: La URL base de la API, de ANDREANI_API_URL.
            timeout: Tiempo máximo de espera por respuesta.
            proxies: Proxy opcional para peticiones HTTP.
        """
        self.api_key = api_key or os.getenv("ANDREANI_API_KEY", "")
        self.base_url = base_url or os.getenv("ANDREANI_API_URL", "https://api.andreani.com/")
        self.timeout = timeout
        self.proxies = proxies

        if not self.api_key:
            logger.warning("AndreaniClient inicializado sin API key.")

    def calculate_shipping(
        self,
        provincia: str,
        localidad: str,
        calle: str,
        numero: str,
    ) -> Decimal:
        """
        Llama al endpoint de cálculo de envío de Andreani y devuelve el costo.

        Args:
            provincia: Nombre de la provincia.
            localidad: Nombre de la localidad/ciudad.
            calle: Nombre de la calle.
            numero: Número de la dirección.

        Returns:
            Decimal: Costo de envío.

        Raises:
            ShippingError: Si hay un error de red, autenticación o la API responde mal.
        """
        url = f"{self.base_url.rstrip('/')}/v1/shipping/calculate"
        payload = {
            "provincia": provincia,
            "localidad": localidad,
            "calle": calle,
            "numero": numero,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with requests.Session() as session:
                session.headers.update(headers)
                resp = session.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    proxies=self.proxies,
                )
            resp.raise_for_status()
            data = resp.json()
            cost = data.get("cost")
            if cost is None:
                raise ShippingError(f"Respuesta inesperada: {data}")
            return Decimal(str(cost))
        except requests.RequestException as e:
            logger.error("Error al llamar a Andreani: %s", e)
            # raise ShippingError("No se pudo calcular el costo de envío++