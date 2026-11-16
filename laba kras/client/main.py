
from __future__ import annotations

import asyncio

import webbrowser 
import os
import base64
from pathlib import Path

import flet as ft
import httpx
from dotenv import load_dotenv

load_dotenv()

DEFAULT_SERVER_URL = os.getenv("SERVER_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
PLACEHOLDER_PATH = ASSETS_DIR / "placeholder_avatar.png"


def get_server_url() -> str:
    return os.getenv("SERVER_PUBLIC_URL", DEFAULT_SERVER_URL).rstrip("/")


def fetch_bot_username(server_url: str) -> str | None:
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{server_url}/bot")
            if r.status_code == 200:
                username = r.json().get("username")
                if username:
                    return username.lstrip("@")
    except Exception:
        pass
    return os.getenv("BOT_USERNAME", "").lstrip("@") or None


def placeholder_data_url() -> str:
    if PLACEHOLDER_PATH.exists():
        b64 = base64.b64encode(PLACEHOLDER_PATH.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    return ""


def image_from_avatar(avatar: str | None) -> ft.Image:
    if avatar:
        return ft.Image(
            src=avatar,
            width=120,
            height=120,
            fit=ft.BoxFit.COVER,
            border_radius=60,
        )
    ph = placeholder_data_url()
    if ph:
        return ft.Image(src=ph, width=120, height=120, fit=ft.BoxFit.COVER, border_radius=60)
    return ft.Image(width=120, height=120)


def show_main_view(page: ft.Page, user: dict) -> None:
    page.controls.clear()
    avatar = image_from_avatar(user.get("avatar"))
    first_name = user.get("first_name") or ""
    last_name = user.get("last_name") or "—"
    username = user.get("username")
    username_text = f"@{username}" if username else "—"

    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("Профиль", size=24, weight=ft.FontWeight.BOLD),
                    avatar,
                    ft.Text(f"Имя: {first_name}", size=16),
                    ft.Text(f"Фамилия: {last_name}", size=16),
                    ft.Text(f"Юзернейм: {username_text}", size=16),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            alignment=ft.Alignment.CENTER,
            expand=True,
            padding=20,
        )
    )
    page.update()


def show_login_view(page: ft.Page) -> None:
    server_url = get_server_url()
    pin_field = ft.TextField(
        label="Ключ (PIN-код)",
        hint_text="Введите 4 цифры",
        width=260,
        max_length=4,
        keyboard_type=ft.KeyboardType.NUMBER,
        autofocus=True,
    )
    status_text = ft.Text(value="", color=ft.Colors.RED)

    def on_login(e):
        pin = (pin_field.value or "").strip()
        if len(pin) != 4 or not pin.isdigit():
            status_text.value = "Введите 4-значный числовой PIN-код"
            status_text.color = ft.Colors.RED
            page.update()
            return
        status_text.value = "Проверка..."
        status_text.color = ft.Colors.BLUE
        page.update()
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.post(f"{get_server_url()}/auth", json={"key": pin})
            if r.status_code == 200:
                show_main_view(page, r.json())
                return
            detail = "Неверный или истёкший PIN-код"
            try:
                data = r.json()
                if isinstance(data, dict) and data.get("detail"):
                    detail = str(data["detail"])
            except Exception:
                pass
            status_text.value = detail
            status_text.color = ft.Colors.RED
        except Exception as ex:
            status_text.value = f"Ошибка подключения: {ex}"
            status_text.color = ft.Colors.RED
        page.update()

    async def open_bot(kind: str):
        username = await asyncio.to_thread(fetch_bot_username, get_server_url())
        if not username:
            status_text.value = "Не удалось определить бота (задайте BOT_USERNAME)"
            status_text.color = ft.Colors.RED
            page.update()
            return
        if kind == "app":
            url = f"tg://resolve?domain={username}"
        else:
            url = f"https://web.telegram.org/k/#@{username}"
        try:
            if page.web:
                await page.launch_url(url)
            else:
                webbrowser.open(url)
        except Exception as ex:
            status_text.value = f"Не удалось открыть ссылку: {ex}"
            status_text.color = ft.Colors.RED
            page.update()

    async def on_open_app(e):
        await open_bot("app")

    async def on_open_web(e):
        await open_bot("web")

    login_button = ft.Button("Войти", on_click=on_login, width=260)
    bot_link_app = ft.TextButton("Открыть в приложении Telegram", on_click=on_open_app)
    bot_link_web = ft.TextButton("Открыть в Telegram Web", on_click=on_open_web)

    page.controls.clear()
    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("Вход", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Сервер: {server_url}", size=12, color=ft.Colors.GREY),
                    pin_field,
                    login_button,
                    bot_link_app,
                    bot_link_web,
                    status_text,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                width=320,
            ),
            alignment=ft.Alignment.CENTER,
            expand=True,
            padding=20,
        )
    )
    page.update()

def main(page: ft.Page):
    page.title = "BE Task 01 - Client"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.window.width = 420
    page.window.height = 580
    show_login_view(page)


if __name__ == "__main__":
    import sys

    if "--web" in sys.argv or os.getenv("FLET_WEB") == "1":
        port = int(os.getenv("FLET_WEB_PORT", "8550"))
        ft.run(main, view=ft.AppView.WEB_BROWSER, port=port, assets_dir=str(ASSETS_DIR))
    else:
        ft.run(main, assets_dir=str(ASSETS_DIR))

