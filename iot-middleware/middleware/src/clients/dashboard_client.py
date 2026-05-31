import logging
import time
from typing import Any

import requests

log = logging.getLogger("middleware.dashboard_client")


class DashboardClient:

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        max_retries: int = 2,
        retry_delay: float = 1.0,
        timeout: float = 5.0,
    ) -> None:
        self.base_url    = base_url.rstrip("/")
        self.username    = username
        self.password    = password
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout     = timeout

        self._token: str | None = None
        self._session = requests.Session()


    def login(self) -> bool:
        url = f"{self.base_url}/api/auth/login"

        for attempt in range(1, self.max_retries + 2):   
            try:
                resp = self._session.post(
                    url,
                    json={"username": self.username, "password": self.password},
                    timeout=self.timeout,
                )

                if resp.status_code == 200:
                    log.info("Autenticação bem-sucedida no dashboard.")
                    self._token = self._extract_token(resp)
                    return True

                log.warning(
                    "Login falhou (HTTP %d): %s",
                    resp.status_code,
                    resp.text[:120],
                )

            except requests.RequestException as exc:
                log.warning("Tentativa %d/%d de login falhou: %s",
                            attempt, self.max_retries + 1, exc)

            if attempt <= self.max_retries:
                time.sleep(self.retry_delay)

        return False

    def _extract_token(self, response: requests.Response) -> str | None:
        """Extrai o JWT do header Set-Cookie da resposta de login."""
        for cookie in response.cookies:
            if cookie.name == "access_token_cookie":
                return cookie.value
        return None

    def _auth_headers(self) -> dict:
        """Retorna headers de autorização Bearer."""
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}


    def send_data(self, payload: dict[str, Any]) -> bool:
        """
        Envia um registro IoT ao endpoint /api/data/ingest do dashboard.

        Comunicação síncrona — bloqueia até obter resposta ou esgotar retries.
        Em caso de token expirado (401), tenta re-autenticar uma vez antes de
        considerar a tentativa como falha.

        Retorna True se o dado foi aceito (2xx), False após esgotar todas as tentativas.
        """
        url = f"{self.base_url}/api/data/ingest"

        for attempt in range(1, self.max_retries + 2):
            try:
                resp = self._session.post(
                    url,
                    json=payload,
                    headers=self._auth_headers(),
                    timeout=self.timeout,
                )

                if resp.status_code in (200, 201):
                    log.debug("Dado enviado com sucesso (tentativa %d).", attempt)
                    return True

                if resp.status_code == 401:
                    log.warning("Token expirado. Tentando re-autenticar...")
                    if self.login():
                        continue
                    log.error("Re-autenticação falhou. Abortando envio.")
                    return False

                log.warning(
                    "Envio falhou (tentativa %d/%d) — HTTP %d: %s",
                    attempt, self.max_retries + 1,
                    resp.status_code, resp.text[:120],
                )

            except requests.RequestException as exc:
                log.warning(
                    "Erro de rede (tentativa %d/%d): %s",
                    attempt, self.max_retries + 1, exc,
                )

            if attempt <= self.max_retries:
                log.info("Aguardando %.1fs antes do retry %d...", self.retry_delay, attempt)
                time.sleep(self.retry_delay)

        log.error("Dado perdido após %d tentativa(s).", self.max_retries + 1)
        return False
