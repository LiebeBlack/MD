"""Autenticacion Microsoft (cuenta oficial) para jugar online.

Implementa el flujo OAuth2 por codigo de dispositivo de Microsoft Identity
Platform y el intercambio Xbox Live -> Minecraft Services, equivalente al
que usan Prism Launcher y ATLauncher. Solo usa la libreria estandar.

El ``CLIENT_ID`` es un cliente publico registrado para flujos device-code
(el mismo enfoque que otros launchers open source). Si en el futuro se
registra una app propia en Azure, basta cambiar esta constante.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable

from .auth import (OfflineProfile, OnlineProfile, create_profile,
                   validate_username)
from .constants import USER_AGENT
from . import database

CLIENT_ID = "c36a9fb6-4f2a-41ff-90bd-ae7cc92031eb"
SCOPE = "XboxLive.signin offline_access"

_DEVICE_CODE_URL = ("https://login.microsoftonline.com/consumers/"
                    "oauth2/v2.0/devicecode")
_TOKEN_URL = ("https://login.microsoftonline.com/consumers/"
              "oauth2/v2.0/token")
_XBOX_AUTH_URL = "https://user.auth.xboxlive.com/user/authenticate"
_XSTS_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
_MC_LOGIN_URL = "https://api.minecraftservices.com/authentication/login_with_xbox"
_MC_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"


class MsaError(RuntimeError):
    pass


class MsaCancelled(RuntimeError):
    pass


@dataclass
class DeviceCode:
    user_code: str
    verification_uri: str
    device_code: str
    interval: int
    expires_in: int


@dataclass
class McSession:
    """Sesion ya canjeada contra Minecraft Services."""
    access_token: str
    name: str
    uuid: str          # sin guiones, como espera el lanzador oficial


def _post_json(url: str, payload: dict, timeout: float = 30.0) -> dict:
    if isinstance(payload, dict):
        body = urllib.parse.urlencode(payload).encode("utf-8")
    elif isinstance(payload, str):
        body = payload.encode("utf-8")
    else:
        body = payload
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            detail = json.loads(error.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            detail = {"error": str(error.code)}
        parts = [str(detail.get("error") or ""),
                 str(detail.get("error_description") or ""),
                 str(detail.get("message") or "")]
        raise MsaError(" ".join(part for part in parts if part).strip()
                       or f"HTTP {error.code} en {url}") from error
    except urllib.error.URLError as error:
        raise MsaError(f"Sin conexion con Microsoft: {error.reason}") from error


def _post_raw_json(url: str, payload: dict, timeout: float = 30.0,
                   bearer: str | None = None) -> dict:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            detail = json.loads(error.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            detail = {"message": str(error.code)}
        raise MsaError(detail.get("message") or f"HTTP {error.code} en {url}")
    except urllib.error.URLError as error:
        raise MsaError(f"Sin conexion: {error.reason}") from error


def _get_json(url: str, bearer: str, timeout: float = 30.0) -> dict:
    request = urllib.request.Request(
        url, method="GET",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT,
                 "Authorization": f"Bearer {bearer}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise MsaError(f"HTTP {error.code} consultando perfil de Minecraft")
    except urllib.error.URLError as error:
        raise MsaError(f"Sin conexion: {error.reason}") from error


# ------------------------------------------------------------ device code
def request_device_code() -> DeviceCode:
    data = _post_json(_DEVICE_CODE_URL, {
        "client_id": CLIENT_ID,
        "scope": SCOPE,
    })
    try:
        return DeviceCode(
            user_code=data["user_code"],
            verification_uri=data.get("verification_uri")
            or data.get("verification_url") or "",
            device_code=data["device_code"],
            interval=max(5, int(data.get("interval", 5))),
            expires_in=int(data.get("expires_in", 900)),
        )
    except KeyError as error:
        raise MsaError("Respuesta invalida del servicio de Microsoft.") from error


def _poll_msa_token(device_code: str, interval: int,
                    expires_in: int,
                    cancel: Callable[[], bool] | None = None) -> dict:
    """Espera a que el usuario complete el inicio de sesion."""
    deadline = time.monotonic() + expires_in
    wait = interval
    while time.monotonic() < deadline:
        if cancel and cancel():
            raise MsaCancelled()
        try:
            data = _post_json(_TOKEN_URL, {
                "client_id": CLIENT_ID,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
            })
            return data
        except MsaError as error:
            message = str(error)
            # Los errores OAuth llegan como texto; se inspecciona el cuerpo.
            if "authorization_pending" in message:
                pass
            elif "slow_down" in message:
                wait += 5
            elif "expired_token" in message:
                raise MsaError("El codigo expiro. Inicia sesion de nuevo.")
            elif "authorization_declined" in message or "access_denied" in message:
                raise MsaError("Inicio de sesion cancelado por el usuario.")
            elif "bad_verification_code" in message:
                raise MsaError("Codigo de verificacion invalido.")
            else:
                raise
        time.sleep(wait)
        if cancel and cancel():
            raise MsaCancelled()
    raise MsaError("El codigo expiro. Intentalo de nuevo.")


# ------------------------------------------------------------- intercambio
def _xbox_user_token(msa_access_token: str) -> tuple[str, str]:
    data = _post_raw_json(_XBOX_AUTH_URL, {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": f"d={msa_access_token}",
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT",
    })
    token = data.get("Token")
    uhs = (((data.get("DisplayClaims") or {}).get("xui") or [{}])[0]
           .get("uhs"))
    if not token or not uhs:
        raise MsaError("Xbox Live no devolvio un token valido. "
                       "Comprueba que la cuenta tenga perfil de Xbox.")
    return token, uhs


def _xsts_token(xbox_token: str, uhs: str) -> str:
    data = _post_raw_json(_XSTS_URL, {
        "Properties": {
            "SandboxId": "RETAIL",
            "UserTokens": [xbox_token],
        },
        "RelyingParty": "rp://api.minecraftservices.com/",
        "TokenType": "JWT",
    })
    token = data.get("Token")
    if not token:
        raise MsaError("No se pudo obtener el token XSTS de Xbox Live.")
    return token


def _minecraft_session(msa_access_token: str) -> McSession:
    xbox_token, uhs = _xbox_user_token(msa_access_token)
    xsts = _xsts_token(xbox_token, uhs)
    login = _post_raw_json(_MC_LOGIN_URL, {
        "identityToken": f"XBL3.0 x={uhs};{xsts}",
    })
    mc_token = login.get("access_token")
    if not mc_token:
        raise MsaError("Minecraft Services rechazo el inicio de sesion.")
    profile = _get_json(_MC_PROFILE_URL, mc_token)
    mc_uuid = (profile.get("id") or "").replace("-", "")
    mc_name = profile.get("name") or ""
    if not mc_uuid or not mc_name:
        raise MsaError("La cuenta no tiene un perfil de Minecraft valido. "
                       "Necesitas Minecraft Java Edition.")
    return McSession(access_token=mc_token, name=mc_name, uuid=mc_uuid)


def refresh_msa_token(refresh_token: str) -> dict:
    return _post_json(_TOKEN_URL, {
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": SCOPE,
    })


def ensure_mc_session(refresh_token: str) -> tuple[McSession, str]:
    """Canjea un refresh token por una sesion de Minecraft valida.

    Devuelve (sesion, nuevo_refresh_token). Lanza MsaError si la cuenta
    ya no es valida y hay que volver a iniciar sesion.
    """
    try:
        tokens = refresh_msa_token(refresh_token)
    except MsaError as error:
        raise MsaError(
            f"La sesion de Microsoft expiro o fue revocada ({error}). "
            "Vuelve a iniciar sesion en la pestana Cuenta."
        ) from error
    msa_token = tokens.get("access_token")
    if not msa_token:
        raise MsaError("Microsoft no devolvio un token de acceso.")
    session = _minecraft_session(msa_token)
    return session, tokens.get("refresh_token") or refresh_token


def login_with_device_code(
    on_code: Callable[[DeviceCode], None] | None = None,
    cancel: Callable[[], bool] | None = None,
) -> tuple[McSession, str]:
    """Flujo completo: device code -> tokens -> sesion de Minecraft.

    Devuelve (sesion, refresh_token) para guardarla en la base de datos.
    """
    device = request_device_code()
    if on_code:
        on_code(device)
    tokens = _poll_msa_token(device.device_code, device.interval,
                             device.expires_in, cancel=cancel)
    msa_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    if not msa_token:
        raise MsaError("Microsoft no devolvio un token de acceso.")
    if not refresh_token:
        raise MsaError("Microsoft no devolvio un refresh token; "
                       "vuelve a intentarlo.")
    return _minecraft_session(msa_token), refresh_token


# ------------------------------------------------------------- perfiles
def resolve_profile(settings):
    """Perfil de juego segun la cuenta activa (offline o Microsoft).

    ``settings.active_account`` vale "" o "offline" para el perfil local,
    o "ms:<uuid>" para una cuenta Microsoft guardada en la base de datos.
    Todo el contenido del launcher es gratuito: la cuenta solo hace falta
    para servidores con online-mode activado.
    """
    key = (getattr(settings, "active_account", "") or "").strip()
    if key.startswith("ms:"):
        row = database.get_account(key[3:])
        if row is None:
            raise MsaError(
                "La cuenta Microsoft guardada ya no existe. "
                "Inicia sesion otra vez en la pestana Cuenta."
            )
        session, new_refresh = ensure_mc_session(row["msa_refresh_token"])
        if new_refresh != row["msa_refresh_token"]:
            database.save_account(row["mc_uuid"], row["mc_name"],
                                  new_refresh)
        return OnlineProfile(name=session.name, uuid=session.uuid,
                             access_token=session.access_token)

    error = validate_username((settings.username or "").strip())
    if error:
        raise MsaError(error)
    return create_profile(settings.username.strip())
