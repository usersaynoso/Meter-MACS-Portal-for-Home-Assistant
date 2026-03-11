from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from .const import BASE_URL
from .helpers import normalize_socket_state, parse_next_action_payload, socket_location_from_values

_LOGGER = logging.getLogger(__name__)


class AuthError(Exception):
    pass


class ScrapeError(Exception):
    pass


@dataclass
class Meter:
    meter_id: str
    name: str
    balance: Optional[float]
    currency: Optional[str]
    site_id: Optional[str] = None
    asset_id: str | int | None = None
    cost_per_kwh: Optional[float] = None
    site_db_id: str | None = None
    asset_db_id: str | None = None
    socket_site: str | None = None
    socket_area: str | None = None
    socket_location: str | None = None
    socket_state: int | None = None
    session_type: str | None = None


class MeterMacsClient:
    def __init__(self, session: aiohttp.ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._base_url = BASE_URL.rstrip("/")
        self._logged_in = False

    async def ensure_logged_in(self) -> None:
        if self._logged_in:
            return
        await self._login()

    async def _get(self, path: str) -> aiohttp.ClientResponse:
        url = urljoin(self._base_url + "/", path.lstrip("/"))
        _LOGGER.debug("GET %s", url)
        resp = await self._session.get(url, allow_redirects=True)
        return resp

    async def _post(self, path_or_url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> aiohttp.ClientResponse:
        url = urljoin(self._base_url + "/", path_or_url)
        _LOGGER.debug("POST %s", url)
        resp = await self._session.post(url, data=data, headers=headers or {}, allow_redirects=True)
        return resp

    async def _login(self) -> None:
        # Preferred auth: Better Auth email sign-in endpoint
        try:
            url = "/api/auth/sign-in/email"
            payload = {"email": self._email, "password": self._password, "rememberMe": False}
            resp = await self._session.post(
                urljoin(self._base_url + "/", url.lstrip("/")),
                json=payload,
                allow_redirects=True,
            )
            if resp.status == 200:
                # Consider logged in if token present or cookie set
                try:
                    body = await resp.json(content_type=None)
                except Exception:  # noqa: BLE001
                    body = {}
                if body or resp.headers.get("set-cookie"):
                    self._logged_in = True
                    _LOGGER.debug("Login successful via /api/auth/sign-in/email")
                    return
        except Exception:  # noqa: BLE001
            pass

        # Fallback: try to reach dashboard; if redirected to login, attempt to submit form
        resp = await self._get("/dashboard")
        text = await resp.text()
        if resp.status == 200 and not self._looks_like_login_page(text):
            _LOGGER.debug("Already logged in (dashboard accessible)")
            self._logged_in = True
            return

        login_candidates = ["/login", "/signin", "/auth/login", "/"]
        login_html = text
        for candidate in login_candidates:
            try:
                resp2 = await self._get(candidate)
                login_html = await resp2.text()
                if self._looks_like_login_page(login_html):
                    break
            except Exception:  # noqa: BLE001
                continue

        form_info = self._extract_login_form(login_html)
        if form_info is None:
            raise AuthError("Unable to locate login form")

        action, form_data, headers = form_info
        email_key = self._guess_email_field(form_data)
        password_key = self._guess_password_field(form_data)
        if not email_key or not password_key:
            raise AuthError("Unable to identify form fields for email/password")

        form_data[email_key] = self._email
        form_data[password_key] = self._password

        resp3 = await self._post(action, data=form_data, headers=headers)
        _ = await resp3.text()

        check = await self._get("/dashboard")
        check_text = await check.text()
        if check.status == 200 and not self._looks_like_login_page(check_text):
            self._logged_in = True
            _LOGGER.debug("Login successful via HTML form fallback")
            return
        raise AuthError("Invalid authentication or login failed")

    def _looks_like_login_page(self, html: str) -> bool:
        soup = BeautifulSoup(html, "html.parser")
        # Heuristics: presence of a password input usually indicates a login form
        pwd = soup.find("input", {"type": "password"})
        return pwd is not None

    def _extract_login_form(self, html: str) -> Optional[Tuple[str, Dict[str, Any], Dict[str, str]]]:
        soup = BeautifulSoup(html, "html.parser")
        # Choose the first form that contains a password field
        form = None
        for f in soup.find_all("form"):
            if f.find("input", {"type": "password"}):
                form = f
                break
        if not form:
            return None

        action = form.get("action") or "/login"
        action = action if action.startswith("http") else urljoin(self._base_url + "/", action)

        data: Dict[str, Any] = {}
        for inp in form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            value = inp.get("value", "")
            data[name] = value

        headers = {}
        # Anti-CSRF tokens are typically included as hidden inputs and do not require special headers
        # but a Referer sometimes helps
        headers["Referer"] = action

        return action, data, headers

    def _guess_email_field(self, data: Dict[str, Any]) -> Optional[str]:
        candidates = [
            "email",
            "username",
            "user",
            "login",
            "identity",
            "user[email]",
            "user[username]",
        ]
        lowered = {k.lower(): k for k in data.keys()}
        for key in candidates:
            if key in lowered:
                return lowered[key]
        # Fallback: any input whose name contains email
        for k in data.keys():
            if "email" in k.lower() or "user" == k.lower():
                return k
        return None

    def _guess_password_field(self, data: Dict[str, Any]) -> Optional[str]:
        candidates = ["password", "pass", "pwd", "user[password]"]
        lowered = {k.lower(): k for k in data.keys()}
        for key in candidates:
            if key in lowered:
                return lowered[key]
        for k in data.keys():
            if "pass" in k.lower():
                return k
        return None

    async def fetch_dashboard(self) -> str:
        await self.ensure_logged_in()
        resp = await self._get("/dashboard")
        if resp.status != 200:
            raise ScrapeError(f"Unexpected status: {resp.status}")
        return await resp.text()


async def _read_json_response(resp: aiohttp.ClientResponse) -> dict:
    # Endpoints may respond with content-type text/plain; parse manually
    text = await resp.text()
    try:
        return json.loads(text)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("JSON parse failed; first 200 bytes: %s", text[:200])
        raise ScrapeError("Failed to parse JSON response") from exc


class ApiNotAvailable(Exception):
    pass


class SupplyActionError(Exception):
    pass


class SiteNotFound(Exception):
    pass


class AssetNotFound(Exception):
    pass


class MeterApi:
    """High-level API built on top of MeterMacsClient for JSON endpoints."""

    def __init__(self, client: MeterMacsClient) -> None:
        self._client = client
        self._server_action_url = f"{self._client._base_url.rstrip('/')}/dashboard"

    async def _post_server_action(self, action_id: str, payload: list[dict]) -> dict:
        await self._client.ensure_logged_in()
        resp = await self._client._session.post(
            self._server_action_url,
            data=json.dumps(payload),
            headers={
                "Accept": "text/x-component",
                "Content-Type": "application/json",
                "Next-Action": action_id,
                "Origin": self._client._base_url,
                "Referer": self._server_action_url,
            },
            allow_redirects=True,
        )
        if resp.status != 200:
            raise ScrapeError(f"Unexpected status {resp.status} from server action {action_id}")
        text = await resp.text()
        try:
            return parse_next_action_payload(text)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Failed to parse server action payload: %s", text[:400])
            raise ScrapeError("Failed to parse server action response") from exc

    async def _get_json(self, path: str) -> dict:
        await self._client.ensure_logged_in()
        resp = await self._client._get(path)
        if resp.status == 404:
            raise ApiNotAvailable(f"Endpoint not found: {path}")
        if resp.status != 200:
            raise ScrapeError(f"Unexpected status {resp.status} for {path}")
        return await _read_json_response(resp)

    async def get_session(self) -> dict:
        """Return session payload with user, sites and assets."""
        return await self._get_json("/api/auth/get-session")

    async def fetch_assets(self, site_id: str) -> list[dict]:
        data = await self._get_json(f"/api/sites/{site_id}/assets")
        if data.get("status") != "success":
            return []
        assets = data.get("data", {}).get("assets", [])
        return assets or []

    async def fetch_asset_details(self, site_id: str, asset_id: str | int) -> dict:
        # Numeric id is used in endpoint
        try:
            numeric_id = int(str(asset_id).lstrip("0") or "0")
        except Exception:  # noqa: BLE001
            numeric_id = asset_id
        data = await self._get_json(f"/api/sites/{site_id}/assets/{numeric_id}")
        if data.get("status") != "success":
            raise AssetNotFound(str(asset_id))
        return data.get("data", {})

    async def fetch_cost_per_kwh(self, site_id: str, asset_id: str | int) -> Optional[float]:
        """Return standardRate with a 5% uplift from dashboard session data.

        Endpoint: /api/dashboard-data/{siteId}/{assetId}/session?utilityType=electricity
        """
        try:
            numeric_id = int(str(asset_id).lstrip("0") or "0")
        except Exception:  # noqa: BLE001
            numeric_id = asset_id
        path = f"/api/dashboard-data/{site_id}/{numeric_id}/session?utilityType=electricity"
        data = await self._get_json(path)
        if data.get("status") != "success":
            return None
        dd = data.get("data", {})
        session = dd.get("session", {})
        cb = session.get("costBreakdown", {}) if isinstance(session, dict) else {}
        tlist = cb.get("tariffBreakdownList") or []
        if not tlist:
            return None
        first = tlist[0] if isinstance(tlist, list) else None
        if not isinstance(first, dict):
            return None
        rate = first.get("standardRate")
        if isinstance(rate, (int, float)):
            return float(rate) * 1.05
        return None

    async def fetch_asset_session(self, site_id: str, asset_id: str | int) -> dict | None:
        try:
            numeric_id = int(str(asset_id).lstrip("0") or "0")
        except Exception:  # noqa: BLE001
            numeric_id = asset_id
        data = await self._get_json(
            f"/api/dashboard-data/{site_id}/{numeric_id}/session?utilityType=electricity"
        )
        session = data.get("data", {}).get("session") if isinstance(data.get("data"), dict) else None
        return session if isinstance(session, dict) else None

    async def fetch_meters(self) -> List[Meter]:
        """Fetch meters with balances using discovered API endpoints.

        Flow:
        - Authenticate
        - GET /api/auth/get-session -> list sites and assets
        - For each (siteId, assetId) -> GET /api/sites/{siteId}/assets/{numericAssetId}
        """
        session = await self.get_session()
        user = session.get("user", {})
        sites = user.get("sites", []) or []
        meters: List[Meter] = []
        seen_meter_ids: set[str] = set()
        for site_entry in sites:
            site_info = site_entry.get("site", {}) or {}
            site_id = site_info.get("siteId")
            site_db_id = site_info.get("_id")
            if not site_id:
                continue
            for asset in site_entry.get("assets", []) or []:
                asset_id = asset.get("assetId") or asset.get("_id")
                asset_db_id = asset.get("_id")
                # Normalize asset id to ensure stable unique IDs (strip leading zeros)
                try:
                    normalized_asset_id = int(str(asset_id).lstrip("0") or "0")
                except Exception:  # noqa: BLE001
                    normalized_asset_id = asset_id
                asset_name = asset.get("assetName") or asset.get("name") or str(normalized_asset_id)
                try:
                    details = await self.fetch_asset_details(site_id, normalized_asset_id)
                except Exception:  # noqa: BLE001
                    details = {}
                utils = details.get("utilityTypes") or []
                util = utils[0] if utils else None
                balance: Optional[float] = None
                socket_area: Optional[str] = None
                socket_location: Optional[str] = None
                socket_state: Optional[int] = None
                if isinstance(util, dict):
                    bal = util.get("balance")
                    if isinstance(bal, (int, float)):
                        balance = float(bal)
                    socket_area = util.get("areaName")
                    socket_location = util.get("location")
                    socket_state = normalize_socket_state(util.get("socketState"))
                # Fetch electricity cost per kWh with 5% uplift
                try:
                    cost_per_kwh = await self.fetch_cost_per_kwh(site_id, normalized_asset_id)
                except Exception:  # noqa: BLE001
                    cost_per_kwh = None
                try:
                    asset_session = await self.fetch_asset_session(site_id, normalized_asset_id)
                except Exception:  # noqa: BLE001
                    asset_session = None
                meter_unique_id = f"{site_id}_{normalized_asset_id}"
                if meter_unique_id in seen_meter_ids:
                    continue
                seen_meter_ids.add(meter_unique_id)
                meters.append(
                    Meter(
                        meter_id=meter_unique_id,
                        name=(details.get("personalInformation", {}).get("assetName") or asset_name),
                        balance=balance,
                        currency=None,
                        site_id=site_id,
                        asset_id=normalized_asset_id,
                        cost_per_kwh=cost_per_kwh,
                        site_db_id=site_db_id,
                        asset_db_id=asset_db_id,
                        socket_site=(asset_session or {}).get("site"),
                        socket_area=(asset_session or {}).get("area") or socket_area,
                        socket_location=(asset_session or {}).get("location") or socket_location,
                        socket_state=normalize_socket_state((asset_session or {}).get("socketState"))
                        if asset_session
                        else socket_state,
                        session_type=(asset_session or {}).get("type"),
                    )
                )
        return meters

    async def set_supply_state(
        self,
        site_id: str,
        asset_id: str | int,
        state: str,
        *,
        site_db_id: str | None = None,
        asset_name: str | None = None,
        socket_site: str | None = None,
        socket_area: str | None = None,
        socket_location: str | None = None,
    ) -> None:
        """Toggle electricity supply on/off for an asset via portal server actions."""
        desired = state.lower()
        if desired not in {"on", "off"}:
            raise ValueError("state must be 'on' or 'off'")
        try:
            numeric_id: int | str = int(str(asset_id).lstrip("0") or "0")
        except Exception:  # noqa: BLE001
            numeric_id = asset_id
        metadata: dict[str, Any] = {
            "requestId": str(uuid.uuid4()),
        }
        if site_db_id:
            metadata["siteId"] = site_db_id
        if asset_name:
            metadata["assetName"] = asset_name

        if desired == "off":
            result = await self._post_server_action(
                "4023489bc13848baaf82b4d577776bceda69f6f1c2",
                [
                    {
                        "siteId": site_id,
                        "assetId": numeric_id,
                        "serviceType": "electricity",
                        "metadata": metadata,
                    }
                ],
            )
            payload = result.get("data", {}) if isinstance(result, dict) else {}
            if payload.get("success"):
                return
            message = payload.get("message") or result.get("error") or "Failed to disconnect socket"
            raise SupplyActionError(str(message))

        location = socket_location_from_values(socket_site, socket_area, socket_location)
        if location is None:
            raise SupplyActionError(
                "Socket location is unknown. Connect the asset in the Meter MACS portal first so the integration can learn its last socket."
            )
        metadata["location"] = location
        result = await self._post_server_action(
            "407e0ac91d042bb320d46f439aaf2fc8d474cdba7d",
            [
                {
                    "siteId": site_id,
                    "assetId": numeric_id,
                    "serviceType": "electricity",
                    "location": location,
                    "metadata": metadata,
                }
            ],
        )
        payload = result.get("data", {}) if isinstance(result, dict) else {}
        if payload.get("success"):
            return
        message = payload.get("message") or result.get("error") or "Failed to power up socket"
        raise SupplyActionError(str(message))


def parse_dashboard_for_meters(html: str) -> List[Meter]:
    soup = BeautifulSoup(html, "html.parser")
    # Remove non-visible/script content to avoid capturing app bootstrap code as names
    for t in soup(["script", "style", "noscript", "template"]):
        try:
            t.decompose()
        except Exception:  # noqa: BLE001
            continue
    meters: List[Meter] = []

    # Heuristic approach: find labels like Balance/Credit and extract nearby amount
    label_regex = re.compile(r"\b(balance|credit|available)\b", re.IGNORECASE)
    amount_regex = re.compile(
        r"(?P<currency>R|\$|€|£|USD|ZAR|EUR|GBP)?\s*" r"(?P<amount>-?\d{1,3}(?:[ ,]\d{3})*(?:\.\d{1,4})?|\d+)",
    )

    def pick_currency(symbol: Optional[str]) -> Optional[str]:
        if not symbol:
            return None
        s = symbol.upper()
        if s in {"USD", "ZAR", "EUR", "GBP"}:
            return s
        mapping = {"$": "USD", "€": "EUR", "£": "GBP", "R": "ZAR"}
        return mapping.get(symbol, None)

    def slugify(text: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
        return cleaned or "meter"

    seen_ids: set[str] = set()

    for lbl in soup.find_all(string=label_regex):
        container = lbl.parent
        if not container:
            continue

        # Search amount in container first, then neighbors
        search_roots = [container] + list(container.find_all()) + [container.parent] if container.parent else [container]
        amount_value: Optional[float] = None
        currency_value: Optional[str] = None
        for root in search_roots:
            if not root:
                continue
            text = root.get_text(strip=True, separator=" ")
            if not text:
                continue
            m = amount_regex.search(text)
            if m:
                raw_amount = m.group("amount").replace(",", "").replace(" ", "")
                try:
                    amount_value = float(raw_amount)
                except ValueError:
                    continue
                currency_value = pick_currency(m.group("currency"))
                break

        # Guess meter name: look upward for header-like tags
        name_value = None
        for ancestor in [container, container.parent, container.parent.parent if container.parent else None]:
            if not ancestor:
                continue
            for tag in ["h1", "h2", "h3", "h4", "h5", "strong", "header"]:
                header = ancestor.find(tag)
                if header and header.get_text(strip=True):
                    name_value = header.get_text(strip=True)
                    break
            if name_value:
                break
        if not name_value:
            # Conservative fallback: avoid long/garbled bootstrap text
            name_value = "Meter"

        # Bound overly long names that likely come from app bootstrap content
        if not isinstance(name_value, str) or len(name_value) > 60:
            name_value = "Meter"

        meter_id = slugify(name_value)
        # Deduplicate by meter_id
        if meter_id in seen_ids:
            continue
        seen_ids.add(meter_id)

        meters.append(
            Meter(
                meter_id=meter_id,
                name=name_value,
                balance=amount_value,
                currency=currency_value,
                site_id=None,
            )
        )

    return meters

