"""
auth.py
-------
Authentifizierung über Supabase (E-Mail + Passwort).

- Registrierung: E-Mail + Passwort
- Login: E-Mail + Passwort
- Kein Magic-Link (robuster, kein Rate-Limit)
"""

import streamlit as st

from core.supabase_client import get_client


# =========================================================
# SESSION-STATE-KEYS
# =========================================================

KEY_USER = "auth_user"
KEY_SESSION = "auth_session"


# =========================================================
# REGISTRIERUNG
# =========================================================

def sign_up(email: str, password: str) -> tuple[bool, str]:
    """
    Registriert einen neuen Nutzer.

    Rückgabe: (Erfolg, Nachricht)
    """

    email = email.strip().lower()

    if not email or "@" not in email:
        return False, "Bitte eine gültige E-Mail-Adresse eingeben."

    if len(password) < 6:
        return False, "Passwort muss mindestens 6 Zeichen haben."

    client = get_client()

    try:
        response = client.auth.sign_up({
            "email": email,
            "password": password,
        })

        if response.user is None:
            return False, "Registrierung fehlgeschlagen. Unbekannter Fehler."

        # Falls "Confirm email" aktiviert ist, ist session = None
        if response.session is None:
            return True, (
                "Registrierung erfolgreich! Bitte bestätige deine E-Mail "
                "(Postfach prüfen) und melde dich dann an."
            )

        # Sonst direkt eingeloggt
        _set_session(response)
        return True, "Registrierung erfolgreich! Du bist eingeloggt."

    except Exception as exc:
        msg = str(exc)
        if "already registered" in msg.lower() or "already exists" in msg.lower():
            return False, "Diese E-Mail ist bereits registriert. Bitte einloggen."
        return False, f"Fehler: {msg}"


# =========================================================
# LOGIN
# =========================================================

def sign_in(email: str, password: str) -> tuple[bool, str]:
    """
    Loggt einen Nutzer ein.

    Rückgabe: (Erfolg, Nachricht)
    """

    email = email.strip().lower()

    if not email or not password:
        return False, "Bitte E-Mail und Passwort eingeben."

    client = get_client()

    try:
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })

        if response.user is None:
            return False, "Login fehlgeschlagen."

        _set_session(response)
        return True, "Login erfolgreich!"

    except Exception as exc:
        msg = str(exc)
        if "invalid" in msg.lower() or "credentials" in msg.lower():
            return False, "E-Mail oder Passwort ist falsch."
        return False, f"Fehler: {msg}"


# =========================================================
# SESSION-VERWALTUNG
# =========================================================

def _set_session(response):
    """Speichert die Session im Streamlit-State."""
    st.session_state[KEY_USER] = {
        "id": response.user.id,
        "email": response.user.email,
    }
    if response.session:
        st.session_state[KEY_SESSION] = response.session.access_token


def get_current_user() -> dict | None:
    """Gibt den eingeloggten User zurück (oder None)."""
    return st.session_state.get(KEY_USER)


def is_logged_in() -> bool:
    """Prüft, ob ein User eingeloggt ist."""
    return get_current_user() is not None


def logout():
    """Loggt den User aus."""
    client = get_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass

    st.session_state.pop(KEY_USER, None)
    st.session_state.pop(KEY_SESSION, None)


# =========================================================
# PASSWORT RESET
# =========================================================

def send_reset_email(email: str) -> tuple[bool, str]:
    """Schickt einen Reset-Link per Mail."""

    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Bitte eine gültige E-Mail-Adresse eingeben."

    client = get_client()
    try:
        client.auth.reset_password_email(email)
        return True, f"Reset-Link an **{email}** geschickt."
    except Exception as exc:
        return False, f"Fehler: {exc}"


# =========================================================
# LOGIN-UI
# =========================================================

def render_login_form():
    """Zeigt Login- / Registrierungs-Maske."""

    st.markdown(
        """
        <div style="text-align: center; padding: 30px 0 10px 0;">
            <h1 style="margin-bottom: 4px;">Sagers qAnalyzer</h1>
            <p style="color: #888; letter-spacing: 2px; font-size: 12px;">
                SAGERS QUANT
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_login, tab_register, tab_reset = st.tabs(
        ["🔐  Anmelden", "✏️  Registrieren", "🔁  Passwort vergessen"]
    )

    # ---------- Login ----------
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("E-Mail", key="login_email")
            password = st.text_input("Passwort", type="password", key="login_pw")
            submitted = st.form_submit_button(
                "Anmelden",
                type="primary",
                width="stretch",
            )

        if submitted:
            success, msg = sign_in(email, password)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    # ---------- Register ----------
    with tab_register:
        with st.form("register_form"):
            email_r = st.text_input("E-Mail", key="reg_email")
            pw_r = st.text_input(
                "Passwort (mind. 6 Zeichen)",
                type="password",
                key="reg_pw",
            )
            pw_r2 = st.text_input(
                "Passwort wiederholen",
                type="password",
                key="reg_pw2",
            )
            submitted_r = st.form_submit_button(
                "Registrieren",
                type="primary",
                width="stretch",
            )

        if submitted_r:
            if pw_r != pw_r2:
                st.error("Die Passwörter stimmen nicht überein.")
            else:
                success, msg = sign_up(email_r, pw_r)
                if success:
                    st.success(msg)
                    if is_logged_in():
                        st.rerun()
                else:
                    st.error(msg)

    # ---------- Reset ----------
    with tab_reset:
        with st.form("reset_form"):
            email_reset = st.text_input("E-Mail", key="reset_email")
            submitted_reset = st.form_submit_button(
                "Reset-Link senden",
                width="stretch",
            )

        if submitted_reset:
            success, msg = send_reset_email(email_reset)
            if success:
                st.success(msg)
            else:
                st.error(msg)

    st.divider()
    st.caption(
        "🔒 Deine Daten sind durch Row-Level-Security geschützt. "
        "Andere Nutzer können deine Trades nicht sehen."
    )