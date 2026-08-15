import base64
from io import BytesIO
import ctypes
import os
import sys
import socket
os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'
import json
import random
import datetime
import threading
import webbrowser
from kivy.uix.filechooser import FileChooserIconView





# 1. Жесткая настройка конфигурации Kivy ДО импорта остальных модулей графики.
# Отключаем создание раздражающих красных точек при клике правой кнопкой мыши на ПК.
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

# Импортируем ядро времени и управления окнами Kivy
from kivy.clock import Clock
from kivy.core.window import Window

# Импортируем реактивные свойства для автоматического обновления UI при изменении данных
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ СВЯЗИ С СЕРВЕРОМ ---
SERVER_URL = "http://127.0.0.1:8000"
HEADERS = {"token": "my_secret_token_2026"}
MEDIA_CACHE_DIR = ".quiz_media_cache"
os.makedirs(MEDIA_CACHE_DIR, exist_ok=True)

def get_secure_dir():
    """
    Возвращает безопасный путь для записи файлов.
    На ПК: текущая папка (.).
    На Android/iOS: изолированная папка приложения (песочница user_data_dir),
    что предотвращает ошибки записи 'PermissionError' на смартфонах.
    """
    if sys.platform in ('android', 'ios'):
        from kivy.app import App
        return App.get_running_app().user_data_dir
    return "."
from kivymd.app import MDApp
from kivy.uix.screenmanager import Screen, NoTransition
from kivymd.uix.screenmanager import MDScreenManager

from kivy.uix.screenmanager import Screen

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ СЕТЕВОГО ПРИВАТНОГО ЧАТА ---
global_chat_socket = None
current_chat_partner = ""




class QuizApp(MDApp):
    current_user_id = None
    current_username = None
    is_authenticated = BooleanProperty(False)

    def open_messenger_secure_check(self):
        """Временный отладочный режим: пускает в чат без веб-сервера авторизации."""
        # --- СИМУЛИРУЕМ АВТОРИЗАЦИЮ ДЛЯ ТЕСТОВ ЧАТА ---
        # Если вы не вошли в аккаунт, программа сама даст вам имя 'Тестер_ПК'
        if not getattr(self, 'username', None) or self.username == "Пользователь ПК":
            self.username = "Тестер_1"  # Для второго запущенного окна измените вручную на "Тестер_2"

        self.is_authenticated = True  # Принудительно включаем флаг авторизации

        # Беспрепятственно переходим на экран контактов мессенджера
        self.root.current = "messenger_contacts"

    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Green"
        self.title = "Платформа Тестирования"
        Window.bind(on_request_close=self.on_window_close_request)

        self.root = MDScreenManager()
        self.root.transition = NoTransition()

        # Оставляем только те экраны, которые есть в новом quiz.kv
        self.root.add_widget(TestManagementScreen(name="test_management"))
        self.root.add_widget(DeleteTestScreen(name="delete_test"))
        self.root.add_widget(TestSelectScreen(name="test_select"))
        self.root.add_widget(TestSettingsScreen(name="test_settings"))
        self.root.add_widget(QuizEngineScreen(name="quiz_engine"))
        self.root.add_widget(QuizWizardScreen(name="quiz_wizard"))

        return self.root

    def show_snack(self, text, is_error=False):
        # В версии KivyMD 1.1.1 класс называется строго Snackbar!
        from kivymd.uix.snackbar import Snackbar

        # Задаем цвет фона (красный при ошибке, зеленый при успехе)
        bg_color = (0.9, 0.3, 0.3, 1) if is_error else (0.3, 0.7, 0.4, 1)

        # Создаем и сразу открываем уведомление
        Snackbar(
            text=text,
            bg_color=bg_color,
            duration=2
        ).open()

    def on_window_close_request(self, *args):
        if self.sm.current == "quiz_engine" and Window.fullscreen:
            self.show_snack("Идет тестирование! Выход заблокирован.", is_error=True)
            return True
        return False

from kivy.uix.screenmanager import Screen, NoTransition


class LoginScreen(Screen):
    """Экран авторизации (замена LoginWindow из Tkinter)."""

    def do_login(self):
        """Считывает текстовые поля и запускает фоновый поток запроса."""
        username = self.ids.entry_user.text.strip()
        password = self.ids.entry_pass.text.strip()

        if not username or not password:
            MDApp.get_running_app().show_snack("Заполните все поля!", is_error=True)
            return

        self.ids.btn_login.disabled = True
        self.ids.btn_login.text = "Вход..."

        # Перенос многопоточности из исходного кода
        threading.Thread(target=self.network_login, args=(username, password), daemon=True).start()

    def network_login(self, username, password):
        """Сетевой запрос в фоне без заморозки графического интерфейса."""
        app = MDApp.get_running_app()
        try:
            response = requests.post(
                f"{SERVER_URL}/login",
                json={"username": username, "password": password},
                headers=HEADERS,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                app.current_user_id = data.get("user_id")
                app.current_username = username.lower()
                app.is_authenticated = True
                # Безопасный возврат в UI поток (вместо .after(0, ...))
                Clock.schedule_once(lambda dt: self.success_login())
            else:
                try:
                    error_msg = response.json().get("detail", "Неверные данные")
                except:
                    error_msg = "Неверные данные или ошибка сервера."
                Clock.schedule_once(lambda dt: self.fail_login(error_msg))
        except:
            Clock.schedule_once(lambda dt: self.fail_login("Нет связи с сервером. Вход недоступен."))

    def success_login(self):
        app = MDApp.get_running_app()
        app.show_snack(f"Добро пожаловать, {app.current_username}!")
        app.sm.current = "main_menu"
        app.sm.get_screen("main_menu").refresh_profile_ui()
        self.reset_fields()

    def fail_login(self, msg):
        MDApp.get_running_app().show_snack(msg, is_error=True)
        self.reset_fields()

    def reset_fields(self):
        self.ids.entry_user.text = ""
        self.ids.entry_pass.text = ""
        self.ids.btn_login.disabled = False
        self.ids.btn_login.text = "Войти"


class RegisterScreen(Screen):
    """Экран регистрации (замена RegisterWindow из Tkinter)."""

    def do_register(self):
        username = self.ids.entry_user.text.strip()
        password = self.ids.entry_pass.text.strip()

        if not username or not password:
            MDApp.get_running_app().show_snack("Заполните все поля!", is_error=True)
            return

        self.ids.btn_register.disabled = True
        self.ids.btn_register.text = "Регистрация..."

        threading.Thread(target=self.network_register, args=(username, password), daemon=True).start()

    def network_register(self, username, password):
        app = MDApp.get_running_app()
        try:
            response = requests.post(
                f"{SERVER_URL}/register",
                json={"username": username, "password": password},
                headers=HEADERS,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                app.current_user_id = data.get("user_id")
                app.current_username = username.lower()
                app.is_authenticated = True
                Clock.schedule_once(lambda dt: self.success_register())
            else:
                try:
                    error_msg = response.json().get("detail", "Ошибка регистрации")
                except:
                    error_msg = "Ошибка сервера при регистрации."
                Clock.schedule_once(lambda dt: self.fail_register(error_msg))
        except:
            Clock.schedule_once(lambda dt: self.fail_register("Нет связи с сервером. Регистрация недоступна."))

    def success_register(self):
        app = MDApp.get_running_app()
        app.show_snack("Аккаунт успешно создан! Вы автоматически авторизованы.")
        app.sm.current = "main_menu"
        app.sm.get_screen("main_menu").refresh_profile_ui()
        self.reset_fields()

    def fail_register(self, msg):
        MDApp.get_running_app().show_snack(msg, is_error=True)
        self.reset_fields()

    def reset_fields(self):
        self.ids.entry_user.text = ""
        self.ids.entry_pass.text = ""
        self.ids.btn_register.disabled = False
        self.ids.btn_register.text = "Зарегистрироваться"

    class MainMenuScreen(Screen):
        welcome_text = StringProperty("Добро пожаловать! Войдите в сеть или продолжите как Гость.")

        def on_enter(self):
            """Динамически перерисовывает интерфейс в зависимости от статуса входа с защитой от гонки инициализации Kivy."""
            # --- СУПЕР-ЗАЩИТА: Если Kivy еще не успел создать словарь IDS, уходим на микропаузу ---
            if not self.ids:
                Clock.schedule_once(lambda dt: self.on_enter())
                return

            app = MDApp.get_running_app()
            if app.is_authenticated:
                self.welcome_text = f"👤 Вы вошли как: {app.username} ({app.user_role})"
                # Скрываем кнопки входа/регистрации/гостя, показываем Выход
                self.ids.btn_nav_login.opacity = 0
                self.ids.btn_nav_login.disabled = True
                self.ids.btn_nav_register.opacity = 0
                self.ids.btn_nav_register.disabled = True
                self.ids.btn_guest_mode.opacity = 0
                self.ids.btn_guest_mode.disabled = True
                self.ids.btn_nav_logout.opacity = 1
                self.ids.btn_nav_logout.disabled = False
            else:
                self.welcome_text = "Вы работаете в локальном режиме Гостя."
                # Показываем кнопки входа/регистрации/гостя, скрываем Выход
                self.ids.btn_nav_login.opacity = 1
                self.ids.btn_nav_login.disabled = False
                self.ids.btn_nav_register.opacity = 1
                self.ids.btn_nav_register.disabled = False
                self.ids.btn_guest_mode.opacity = 1
                self.ids.btn_guest_mode.disabled = False
                self.ids.btn_nav_logout.opacity = 0
                self.ids.btn_nav_logout.disabled = True

        def activate_guest_mode(self):
            """Переводит приложение в безопасный гостевой режим без сети."""
            app = MDApp.get_running_app()
            app.username = "Гость"
            app.user_role = "Ученик"
            app.is_authenticated = False
            app.show_snack("Включен Гостевой режим. Сетевые функции заблокированы.")
            app.root.current = "test_management"

    def refresh_profile_ui(self):
        """Динамически обновляет текстовое описание статуса профиля."""
        app = MDApp.get_running_app()
        if app.is_authenticated:
            self.profile_text = f"👤 Аккаунт: {app.current_username}"
        else:
            self.profile_text = "Вы вошли как Гость (Офлайн)"

    def logout(self):  # Оставляем ваше старое название метода
        """Разлогинивает пользователя и возвращает меню к начальному выбору."""
        app = MDApp.get_running_app()
        app.username = ""
        app.user_role = ""
        app.is_authenticated = False

        # Обновляем внешний вид кнопок на текущем экране
        self.on_enter()
        app.show_snack("Вы успешно вышли из профиля.")


class TestManagementScreen(Screen):
    status_text = StringProperty("Локальный режим")

    def on_enter(self):
        app = MDApp.get_running_app()
        if app.is_authenticated:
            self.status_text = f"Режим сети: Авторизован как {app.username} ({app.user_role})"
        else:
            self.status_text = "Режим Гостя: Локальная работа без сети"

    def check_ai_access(self):
        """Проверяет доступ к ИИ: гостям вход заблокирован."""
        app = MDApp.get_running_app()
        if not app.is_authenticated:
            app.show_snack("Генерация ИИ доступна только зарегистрированным пользователям!", is_error=True)
            return
        app.root.current = "ai_generator"


class AiGeneratorScreen(Screen):
    """Экран конфигурации и работы генератора тестов нейросетью (замена open_ai_generator)."""
    ad_text = StringProperty("Загрузка актуального баннера...")
    target_link = "https://google.com"

    def on_enter(self):
        """Сбрасывает интерфейс и устанавливает базовый баннер."""
        self.ad_text = "🔥 РЕКЛАМА ОТ ПАРТНЕРОВ:\nУзнай больше о возможностях платформы!"
        self.target_link = "https://google.com"
        self.ids.loading_box.opacity = 0
        self.ids.main_layout.disabled = False

    def start_generation(self):
        """Валидирует данные полей ввода темы и запускает фоновый сетевой поток."""
        topic = self.ids.entry_topic.text.strip()
        try:
            count = int(self.ids.spin_count.text)
        except ValueError:
            MDApp.get_running_app().show_snack("Введите корректное число вопросов!", is_error=True)
            return

        if not topic:
            MDApp.get_running_app().show_snack("Укажите тему теста!", is_error=True)
            return

        # Переключаем интерфейс в режим ожидания (аналог pack_forget)
        self.ids.main_layout.disabled = True
        self.ids.loading_box.opacity = 1

        # Запускаем сетевой поток для работы с ИИ-сервером
        threading.Thread(
            target=self.network_generation_thread,
            args=(topic, count),
            daemon=True
        ).start()

    def network_generation_thread(self, topic, count):
        """Фоновый поток генерации JSON-файла теста нейросетью."""
        app = MDApp.get_running_app()
        payload = {"topic": topic, "count": count, "user_id": app.current_user_id}

        try:
            response = requests.post(
                f"{SERVER_URL}/generate_test",
                json=payload,
                headers=HEADERS,
                timeout=30
            )
            if response.status_code == 200:
                test_data = response.json()

                # Потокобезопасно обновляем ссылки рекламы через Clock
                banner = test_data.get("banner_url")
                link = test_data.get("target_link")
                if banner and link:
                    Clock.schedule_once(lambda dt: self.update_ad_links(banner, link))

                test_title = test_data.get("test_name", "ai_test")
                # Очистка имени файла от запрещенных символов путей ФС
                safe_name = "".join([c for c in test_title if c.isalnum() or c in (" ", "_")]).strip().replace(" ",
                                                                                                               "_").lower()

                # Кроссплатформенное сохранение: на Android запишет в надежную user_data_dir
                filename = os.path.join(get_secure_dir(), f"{safe_name}.json")

                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(test_data, f, ensure_ascii=False, indent=4)

                Clock.schedule_once(lambda dt: self.success_ai_generation(test_title, filename))
            else:
                status = response.status_code
                Clock.schedule_once(lambda dt: self.finish_ai_with_error(f"Сервер вернул ошибку, код: {status}"))
        except requests.exceptions.RequestException:
            Clock.schedule_once(
                lambda dt: self.finish_ai_with_error("Потеряна связь с ИИ-сервером во время генерации."))

    def update_ad_links(self, banner, link):
        self.target_link = link
        self.ad_text = f"🔥 РЕКЛАМА ОТ ПАРТНЕРОВ:\nИсточник: {banner}\nНАЖМИ, ЧТОБЫ УЗНАТЬ ПОДРОБНОСТИ!"

    def on_click_generation_ad(self):
        """Отсылает клик в статистику вашей админки и открывает браузер."""
        try:
            threading.Thread(
                target=lambda: requests.post(f"{SERVER_URL}/track_click", headers=HEADERS, timeout=3),
                daemon=True
            ).start()
            webbrowser.open(self.target_link)
        except:
            pass

    def success_ai_generation(self, test_title, filename):
        app = MDApp.get_running_app()
        app.show_snack(f"Тест '{test_title}' успешно сохранен на устройство!")
        app.sm.current = "test_management"

    def finish_ai_with_error(self, msg):
        MDApp.get_running_app().show_snack(msg, is_error=True)
        self.ids.main_layout.disabled = False
        self.ids.loading_box.opacity = 0


class DeleteTestScreen(Screen):
    """Экран удаления локальных тестов с диска устройства (замена DeleteApp)."""

    def on_enter(self):
        """Вызывается при открытии экрана. Перерисовывает список файлов."""
        self.refresh_list()

    def refresh_list(self):
        """Обновляет список файлов для удаления с проверкой на пустоту папки."""
        from kivymd.uix.list import OneLineIconListItem, IconLeftWidget

        # Очищаем контейнер удаления
        self.ids.delete_container.clear_widgets()

        target_dir = get_secure_dir()
        files = [f for f in os.listdir(target_dir) if f.endswith(".json") and f != "user_presets.json"]

        # Проверка на пустой список
        if not files:
            item = OneLineIconListItem(
                text="Список ваших тестов пуст",
                theme_text_color="Secondary"
            )
            item.disabled = True
            item.add_widget(IconLeftWidget(icon="folder-alert-outline"))
            self.ids.delete_container.add_widget(item)
            return

        # Рендерим файлы. ИСПРАВЛЕНО: Теперь вызывается корректный метод confirm_delete
        for f_name in files:
            clean_name = os.path.splitext(f_name)[0]  # Чистое имя теста без расширения .json
            item = OneLineIconListItem(
                text=str(clean_name),
                on_release=lambda x, fn=f_name, cn=clean_name: self.confirm_delete(fn, cn)
            )
            item.add_widget(IconLeftWidget(icon="delete-forever-outline"))
            self.ids.delete_container.add_widget(item)

    def confirm_delete(self, filename, test_name):
        """Открывает нативное мобильное окно подтверждения удаления."""
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton, MDRaisedButton

        self.dialog = MDDialog(
            title="Подтверждение",
            text=f"Удалить тест '{test_name}' с устройства безвозвратно?",
            buttons=[
                MDFlatButton(
                    text="ОТМЕНА",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text="УДАЛИТЬ",
                    md_bg_color=(0.9, 0.2, 0.2, 1),
                    # При нажатии закрываем диалог и физически стираем файл
                    on_release=lambda x: [self.dialog.dismiss(), self.execute_delete(filename)]
                )
            ]
        )
        self.dialog.open()

    def execute_delete(self, filename):
        """Физически удаляет JSON-файл с диска устройства и обновляет экран."""
        full_path = os.path.join(get_secure_dir(), filename)
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                MDApp.get_running_app().show_snack("Тест успешно удален с устройства!")
                # Перерисовываем список, чтобы удаленный тест мгновенно пропал с экрана
                self.refresh_list()
        except Exception as e:
            MDApp.get_running_app().show_snack(f"Ошибка удаления: {e}", is_error=True)

    def execute_delete(self, filename):
        """Выполняет окончательное удаление файла с жесткого диска или памяти смартфона."""
        self.dialog.dismiss()
        full_path = os.path.join(get_secure_dir(), filename)
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                MDApp.get_running_app().show_snack("Файл успешно удален!")
        except Exception as e:
            MDApp.get_running_app().show_snack(f"Ошибка удаления: {e}", is_error=True)

        # Обновляем список на экране после удаления
        self.refresh_list()


class TestSelectScreen(Screen):
    """Экран выбора теста (заменяет десктопный Listbox)."""
    local_tests = {}
    cloud_tests = {}

    def on_enter(self):
        """Мгновенно считывает локальные файлы, а облачные подтягивает в фоне."""
        self.load_local_files()
        app = MDApp.get_running_app()
        if app.is_authenticated:
            self.ids.loading_label.text = "🔄 Синхронизация с облаком..."
            threading.Thread(target=self.fetch_cloud_tests, daemon=True).start()
        else:
            self.ids.loading_label.text = ""

    def load_local_files(self):
        """Сканирует кроссплатформенную директорию на валидность JSON-тестов."""
        self.local_tests.clear()
        target_dir = get_secure_dir()

        for filename in os.listdir(target_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(target_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        name = data.get("test_name")
                        if name and "questions" in data:
                            self.local_tests[name] = file_path
                except:
                    pass
        self.update_list_ui()

    def fetch_cloud_tests(self):
        """Стягивает список доступных облачных тестов пользователя в фоне."""
        app = MDApp.get_running_app()
        try:
            response = requests.get(f"{SERVER_URL}/get_user_tests/{app.current_user_id}", timeout=5)
            if response.status_code == 200:
                self.cloud_tests.clear()
                for t in response.json():
                    self.cloud_tests[t['test_name']] = t["id"]
        except:
            pass
        Clock.schedule_once(lambda dt: self.finish_cloud_sync())

    def finish_cloud_sync(self):
        self.ids.loading_label.text = ""
        self.update_list_ui()

    def update_list_ui(self):
        """Перерисовывает нативный список тестов на экране с проверкой на пустоту."""
        from kivymd.uix.list import OneLineIconListItem, IconLeftWidget
        self.ids.container.clear_widgets()

        # --- НАША ПРОВЕРКА НА ПУСТОЙ СПИСОК ТЕСТОВ ---
        if not self.local_tests and not self.cloud_tests:
            item = OneLineIconListItem(
                text="Список ваших тестов пуст",
                theme_text_color="Secondary"
            )
            item.disabled = True  # Делаем надпись некликабельной
            # Добавляем красивую иконку предупреждения/пустоты
            item.add_widget(IconLeftWidget(icon="folder-alert-outline"))
            self.ids.container.add_widget(item)
            return  # Выходим из метода, дальше циклы крутить не нужно

        # Рендерим локальные файлы с иконкой диска (если они есть)
        for name, path in self.local_tests.items():
            item = OneLineIconListItem(text=name, on_release=lambda x, p=path: self.open_settings(p, False))
            item.add_widget(IconLeftWidget(icon="file-document-outline"))
            self.ids.container.add_widget(item)

        # Рендерим облачные тесты с иконкой облака (если они есть)
        for name, cid in self.cloud_tests.items():
            item = OneLineIconListItem(text=f"☁️ {name}", on_release=lambda x, i=cid: self.open_settings(i, True))
            item.add_widget(IconLeftWidget(icon="cloud-outline"))
            self.ids.container.add_widget(item)


    def open_settings(self, file_or_id, is_cloud):
        app = MDApp.get_running_app()
        app.root.get_screen("test_settings").setup_test(file_or_id, is_cloud)
        app.root.current = "test_settings"


class TestSettingsScreen(Screen):
    """Экран предстартовой конфигурации параметров (заменяет SettingsWindow)."""
    test_name_text = StringProperty("")
    punishment = "Блокировка экрана"

    def on_enter(self):
        """Срабатывает при входе на экран. Ставит дефолтный выбор."""
        self.punishment = "Без наказания"
        self.ids.radio_none.active = True



    def setup_test(self, file_or_id, is_cloud):
        self.file_or_id = file_or_id
        self.is_cloud = is_cloud
        self.test_name_text = f"Настройка теста:\n{os.path.basename(str(file_or_id))}"

    def set_punishment(self, name):
        """Коллбэк выбора типа наказания (заменяет tk.Radiobutton)."""
        self.punishment = name

    def start_test(self):
        """Считывает, валидирует числовые параметры и передает их в движок."""
        try:
            # Считываем настройки напрямую из новых полей ввода вашего quiz.kv
            max_errors = int(self.ids.entry_max_errors.text.strip())
            total_time_seconds = int(self.ids.entry_time_limit.text.strip())
            total_delay_seconds = int(self.ids.entry_delay.text.strip())

            if min(max_errors, total_time_seconds, total_delay_seconds) < 0:
                raise ValueError
        except ValueError:
            MDApp.get_running_app().show_snack("Введите корректные положительные числа во все поля ввода!",
                                               is_error=True)
            return

        if total_time_seconds <= 0:
            MDApp.get_running_app().show_snack("Время на ответ не может быть равным 0 секунд!", is_error=True)
            return

        # Формируем словарь конфигурации игрового процесса под ваш quiz_engine
        config = {
            "shuffle": True,  # По умолчанию перемешиваем вопросы локально
            "show_hints": self.ids.chk_hints.active,  # Берем значение из чекбокса подсказок нового .kv
            "time_limit": total_time_seconds,
            "delay_between": total_delay_seconds,
            "max_errors": max_errors,
            "punishments": self.punishment  # Используем выбранное наказание из круглых точек
        }

        app = MDApp.get_running_app()
        # Запускаем игровой движок, используя сохраненный в setup_test путь к файлу (self.file_or_id)
        app.root.get_screen("quiz_engine").start_quiz_game(self.file_or_id, self.is_cloud, config)
        app.root.current = "quiz_engine"


class QuizEngineScreen(Screen):
    """Первая половина игрового движка тестирования (замена QuizWindow)."""
    status_text = StringProperty("Загрузка контента...")
    timer_text = StringProperty("")
    question_text = StringProperty("")
    ad_text = StringProperty("")
    image_counter_text = StringProperty("")

    questions = []
    current_question_idx = 0
    score = 0
    errors_made = 0
    delay_left = 0
    time_left = 0
    valid_images = []
    current_img_idx = 0
    checkbox_vars = {}
    correct_answers = []
    banner_url = ""
    target_link = "https://google.com"

    def force_window_to_foreground(self):
        """Принудительно разворачивает окно Kivy и выводит его на передний план поверх всех окон Windows."""
        if sys.platform == "win32":
            try:
                # Находим аппаратный дескриптор (HWND) окна нашего приложения по его заголовку
                app_title = "Платформа Тестирования"
                hwnd = ctypes.windll.user32.FindWindowW(None, app_title)

                if hwnd:
                    # 1. Показываем и разворачиваем окно, если оно было свернуто
                    SW_RESTORE = 9
                    ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)

                    # 2. Вытаскиваем окно на самый верхний слой (Поверх всех окон)
                    HWND_TOPMOST = -1
                    SWP_NOMOVE = 0x0002
                    SWP_NOSIZE = 0x0001
                    SWP_SHOWWINDOW = 0x0040
                    ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)

                    # 3. Передаем фокус ввода клавиатуры и мыши в наше приложение
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception as e:
                print(f"[ОТЛАДКА] Ошибка Win32 API при вызове фокуса: {e}")

    def start_quiz_game(self, file_path, is_cloud, config):
        """Запускает тестирование и жестко блокирует экран в полноэкранный режим."""
        # --- ИСПРАВЛЕНИЕ 1: ПРИНУДИТЕЛЬНЫЙ ПОЛНОЭКРАННЫЙ РЕЖИМ ---
        Window.fullscreen = 'auto'

        self.ids.btn_submit.text = "Подтвердить ответ"
        self.ids.btn_abort.opacity = 1
        self.ids.btn_abort.disabled = False

        self.config, self.current_question_idx, self.score, self.errors_made = config, 0, 0, 0
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.questions = data.get("questions", [])
        except:
            self.questions = []

        if not self.questions:
            self.force_exit()
            return

        self.start_initial_pause()

    def load_quiz_data_thread(self, file_or_id, is_cloud):
        """Потокобезопасный импорт структуры вопросов локально или из веб-облака."""
        try:
            if is_cloud:
                response = requests.get(f"{SERVER_URL}/get_single_test/{file_or_id}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                else:
                    Clock.schedule_once(lambda dt: self.abort_quiz("Не удалось получить тест с облачного сервера."))
                    return
            else:
                with open(file_or_id, "r", encoding="utf-8") as f:
                    data = json.load(f)

            self.questions = data.get("questions", [])
            self.banner_url = data.get("banner_url", "Партнеры 2026")
            self.target_link = data.get("target_link", "https://google.com")

            if self.config["shuffle"]:
                random.shuffle(self.questions)

            # Передаем управление в главный поток для старта предстартовой паузы
            Clock.schedule_once(lambda dt: self.start_initial_pause())
        except Exception as e:
            Clock.schedule_once(lambda dt: self.abort_quiz(f"Ошибка файловой структуры:\n{e}"))

    def abort_quiz(self, error_msg):
        MDApp.get_running_app().show_snack(error_msg, is_error=True)
        self.force_exit()

    def start_initial_pause(self):
        """Включает экран ожидания и полностью стирает контент предыдущего вопроса (чекбоксы, фото, счетчики)."""
        Window.fullscreen = False
        self.status_text = "Приготовьтесь к следующему вопросу..."
        self.ad_text = "🔥 ЗАГРУЗКА..."

        # --- СТИРАЕМ ТЕКСТ И ВАРИАНТЫ ОТВЕТОВ СТАРОГО ВОПРОСА ---
        self.question_text = ""
        self.ids.options_box.clear_widgets()
        self.checkbox_vars = {}

        # --- ПОЛНОСТЬЮ СХЛОПЫВАЕМ И ОБНУЛЯЕМ СЛАЙДЕР КАРТИНОК И СТРЕЛКИ ---
        self.ids.slider_container.size_hint_y = None
        self.ids.slider_container.height = 0
        self.ids.img_display.source = ""
        self.image_counter_text = ""

        # Прячем панель навигации (стрелочки переключения картинок)
        self.ids.slider_nav_bar.opacity = 0
        self.ids.slider_nav_bar.disabled = True
        self.ids.slider_nav_bar.height = 0

        # Блокируем кнопку подтверждения во время паузы, чтобы пользователь не кликал впустую
        self.ids.btn_submit.disabled = True

        # Запускаем таймер предстартовой паузы
        self.delay_left = self.config["delay_between"]
        Clock.unschedule(self.update_delay_timer)
        Clock.schedule_interval(self.update_delay_timer, 1)

    def update_delay_timer(self, dt):
        """Обновляет таймер паузы ожидания. Больше минуты -> ММ:СС, меньше минуты -> Текст."""

        self.force_window_to_foreground()
        # --- УМНАЯ ЛОГИКА ОТОБРАЖЕНИЯ ВРЕМЕНИ ОЖИДАНИЯ ---
        if self.delay_left >= 60:
            # Если время ожидания больше или равно минуте — выводим цифровой формат ММ:СС
            mins = self.delay_left // 60
            secs = self.delay_left % 60
            self.timer_text = f"Следующий вопрос через: {mins:02d}:{secs:02d}"
        else:
            # Как только осталось меньше минуты — переключаемся на красивый текст со склонениями
            if self.delay_left in (2, 3, 4, 22, 23, 24, 32, 33, 34, 42, 43, 44, 52, 53, 54):
                sec_word = "секунды"
            elif self.delay_left in (1, 21, 31, 41, 51):
                sec_word = "секунду"
            else:
                sec_word = "секунд"

            self.timer_text = f"Следующий вопрос через: {self.delay_left} {sec_word}"

        # Жестко глушим любые всплывающие слайдеры картинок во время паузы
        self.image_counter_text = ""
        self.ids.slider_nav_bar.opacity = 0
        self.ids.slider_nav_bar.disabled = True
        self.ids.slider_nav_bar.height = 0

        if self.delay_left > 0:
            self.delay_left -= 1
        else:
            Clock.unschedule(self.update_delay_timer)
            self.display_question()

    def display_question(self):
        """Выводит вопрос, умные чекбоксы, разворачивает EXIF и отображает любые форматы (PNG/JPG) по реальным байтам."""
        # --- ШАГ 1: БЛОКИРУЕМ СВЕРТЫВАНИЕ И АКТИВИРУЕМ КНОПКУ ---
        Window.fullscreen = 'auto'
        self.ids.btn_submit.disabled = False
        self.force_window_to_foreground()

        q_data = self.questions[self.current_question_idx]
        self.status_text = f"Вопрос {self.current_question_idx + 1} из {len(self.questions)} | Ошибки: {self.errors_made}/{self.config['max_errors']}"
        self.question_text = q_data.get("question_text", "")
        self.ad_text = "🔥 РЕКЛАМА: Сдайте тест без ошибок!"

        # --- ШАГ 2: УМНАЯ ГРУППИРОВКА ЧЕКБОКСОВ (РАДИОКНОПКИ) ---
        self.correct_answers = q_data.get("correct_answers", [])
        opts = list(self.correct_answers) + list(q_data.get("incorrect_answers", []))
        random.shuffle(opts)

        # Если правильный ответ ВСЕГО ОДИН, включаем режим радиокнопок
        is_single_choice = (len(self.correct_answers) == 1)

        from kivymd.uix.selectioncontrol import MDCheckbox
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel

        self.ids.options_box.clear_widgets()
        self.checkbox_vars = {}

        for o in opts:
            row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="40dp", spacing="10dp")

            if is_single_choice:
                chk = MDCheckbox(group="answers", size_hint=(None, None), size=("40dp", "40dp"),
                                 pos_hint={"center_y": 0.5})
            else:
                chk = MDCheckbox(size_hint=(None, None), size=("40dp", "40dp"), pos_hint={"center_y": 0.5})

            lbl = MDLabel(text=str(o), valign="middle", pos_hint={"center_y": 0.5})
            row.add_widget(chk)
            row.add_widget(lbl)
            self.ids.options_box.add_widget(row)
            self.checkbox_vars[o] = chk

        # Запускаем основной таймер времени
        self.time_left = self.config["time_limit"]
        Clock.unschedule(self.update_question_timer)
        Clock.schedule_interval(self.update_question_timer, 1)

        # --- ШАГ 3: УНИВЕРСАЛЬНОЕ ДЕКОДИРОВАНИЕ КАРТИНОК (ПРОВЕРКА БАЙТОВ) ---
        raw_media = q_data.get("media_files", [])
        self.valid_images = []

        temp_cache_dir = os.path.join(get_secure_dir(), ".runtime_media_cache")
        try:
            os.makedirs(temp_cache_dir, exist_ok=True)
            for idx, media_item in enumerate(raw_media):
                media_str = str(media_item).strip()
                if media_str.startswith("data:image"):
                    if "," in media_str:
                        header, encoded = media_str.split(",", 1)
                    else:
                        encoded = media_str

                    missing_padding = len(encoded) % 4
                    if missing_padding:
                        encoded += '=' * (4 - missing_padding)

                    image_data = base64.b64decode(encoded.encode('utf-8'))

                    # --- ЖЕЛЕЗОБЕТОННАЯ ПРОВЕРКА ПО РЕАЛЬНЫМ БАЙТАМ ФАЙЛА ---
                    ext = "jpg"
                    if image_data.startswith(b'\x89PNG'):
                        ext = "png"
                    elif image_data.startswith(b'GIF8'):
                        ext = "gif"

                    # Создаем файл с честным расширением и уникальной микросекундой времени
                    timestamp = datetime.datetime.now().microsecond + idx
                    temp_file_path = os.path.abspath(
                        os.path.join(temp_cache_dir, f"temp_q_{self.current_question_idx}_{timestamp}.{ext}"))

                    with open(temp_file_path, "wb") as temp_file:
                        temp_file.write(image_data)

                    # Авторазворот картинки Pillow по метаданным EXIF
                    try:
                        from PIL import Image as PILImage, ImageOps
                        with PILImage.open(temp_file_path) as pil_img:
                            fixed_img = ImageOps.exif_transpose(pil_img)
                            fixed_img.save(temp_file_path)
                    except:
                        pass

                    # Сбрасываем кэш текстур Kivy по этому новому файлу
                    from kivy.cache import Cache
                    Cache.remove('kv.image', temp_file_path)
                    Cache.remove('kv.texture', temp_file_path)

                    self.valid_images.append(temp_file_path)

                elif media_str and os.path.exists(media_str):
                    self.valid_images.append(media_str)
        except Exception as e:
            print(f"[БЕЗОПАСНЫЙ СБРОС КАРТИНКИ]: {e}")

        # --- ШАГ 4: ОТРИСОВКА ИГРОВОГО СЛАЙДЕРА КАРТИНОК ---
        if self.valid_images:
            self.current_img_idx = 0
            self.ids.slider_container.size_hint_y = 0.35
            self.update_slider_view()
            if len(self.valid_images) == 1:
                self.ids.slider_nav_bar.opacity = 0
                self.ids.slider_nav_bar.disabled = True
                self.ids.slider_nav_bar.height = 0
            else:
                self.ids.slider_nav_bar.opacity = 1
                self.ids.slider_nav_bar.disabled = False
                self.ids.slider_nav_bar.height = "32dp"
        else:
            self.ids.slider_container.size_hint_y = None
            self.ids.slider_container.height = 0

    def update_slider_view(self):
        """Обновляет показ картинки в игровом слайдере с защитой от кэша."""
        if self.valid_images:
            # Применяем отключение кэша прямо к главному экрану картинок тестирования
            self.ids.img_display.nocache = True
            self.ids.img_display.source = self.valid_images[self.current_img_idx]
            self.image_counter_text = f"{self.current_img_idx + 1}/{len(self.valid_images)}"

    def prev_img(self):
        if self.valid_images and self.current_img_idx > 0:
            self.current_img_idx -= 1
            self.update_slider_view()

    def next_img(self):
        if self.valid_images and self.current_img_idx < len(self.valid_images) - 1:
            self.current_img_idx += 1
            self.update_slider_view()

    def update_question_timer(self, dt):
        """Ежесекундно уменьшает лимит времени и выводит его в формате ММ:СС."""
        if self.time_left > 0:
            self.time_left -= 1

            # Рассчитываем минуты и секунды
            mins = self.time_left // 60
            secs = self.time_left % 60

            # Форматируем строку, чтобы всегда было две цифры (например, 05:43 вместо 5:43)
            # Изменяем текст, убирая лишние слова, оставляя только чистые цифровые часы
            self.timer_text = f"Оставшееся время: {mins:02d}:{secs:02d}"
        else:
            Clock.unschedule(self.update_question_timer)
            # Если время вышло, фиксируем ошибку по таймауту
            self.handle_mistake(timeout=True)

    def check_answer(self):
        """Проверяет ответ или возвращает в меню, если тест завершен."""
        if self.ids.btn_submit.text == "Вернуться в меню":
            self.force_exit()
            return

        selected = [opt for opt, chk in self.checkbox_vars.items() if chk.active]
        if not selected:
            MDApp.get_running_app().show_snack("Выберите хотя бы один вариант ответа!", is_error=True)
            return

        Clock.unschedule(self.update_question_timer)

        if sorted(selected) == sorted(self.correct_answers):
            self.score += 1
            MDApp.get_running_app().show_snack("Правильно! 🎉")
            self.current_question_idx += 1

            # --- ИСПРАВЛЕНИЕ: Проверяем, был ли это последний вопрос тестов ---
            if self.current_question_idx >= len(self.questions):
                self.show_results()
            else:
                # Если вопросы еще остались, запускаем межвопросовую паузу
                self.start_initial_pause()
        else:
            self.handle_mistake()

    def handle_mistake(self, timeout=False):
        """Фиксирует ошибку и проверяет лимит для активации наказания."""
        self.errors_made += 1
        if self.errors_made > self.config["max_errors"]:
            self.execute_punishment()
            return

        if self.config["show_hints"] and not timeout:
            MDApp.get_running_app().show_snack(f"Неверно! Ожидалось: {', '.join(self.correct_answers)}", is_error=True)
        else:
            MDApp.get_running_app().show_snack("Ошибка зафиксирована!", is_error=True)

        self.current_question_idx += 1

        # --- ИСПРАВЛЕНИЕ: Проверяем на завершение теста после ошибки ---
        if self.current_question_idx >= len(self.questions):
            self.show_results()
        else:
            self.start_initial_pause()

    def execute_punishment(self):
        """Срабатывает при проигрыше. Полностью очищает UI и обрабатывает наказание."""
        Clock.unschedule(self.update_question_timer)
        Clock.unschedule(self.update_delay_timer)
        p_type = self.config["punishment"]

        # Полностью глушим верхние статус-бары и таймеры времени
        self.status_text = ""
        self.timer_text = ""

        # Прячем слайдеры картинок, счетчики и стрелочки
        self.ids.slider_container.size_hint_y = None
        self.ids.slider_container.height = 0
        self.ids.img_display.source = ""
        self.image_counter_text = ""
        self.ids.slider_nav_bar.opacity = 0
        self.ids.slider_nav_bar.disabled = True
        self.ids.slider_nav_bar.height = 0

        # Мягкий режим без наказания
        if p_type == "Без наказания":
            Window.fullscreen = False
            self.ids.options_box.clear_widgets()
            self.question_text = f"🛑 ТЕСТ ЗАВЕРШЕН ДОСРОЧНО!\n\nПревышен лимит ошибок.\nВы правильно ответили на {self.score} вопр.\nШтрафные санкции: Отсутствуют."

            self.ids.btn_submit.text = "Вернуться в меню"
            self.ids.btn_submit.disabled = False
            self.ids.btn_abort.opacity = 0
            self.ids.btn_abort.disabled = True
            return

        # Жесткие ПК-наказания (только для Windows)
        Window.fullscreen = 'auto'
        if sys.platform == "win32":
            if p_type == "Блокировка экрана":
                os.system("rundll32.exe user32.dll,LockWorkStation")
            elif p_type == "Перезагрузка компьютера":
                os.system("shutdown /r /t 0 /f")
                sys.exit()
            elif p_type == "Выключение компьютера":
                os.system("shutdown /s /t 0 /f")
                sys.exit()

        # Экран тотальной блокировки интерфейса (для мобильных штрафов)
        self.ids.options_box.clear_widgets()
        self.question_text = f"🛑 ТЕСТ ПРОВАЛЕН!\nПревышен лимит ошибок.\n\nИнтерфейс заблокирован за списывание.\nНаказание: {p_type}"

        self.ids.btn_submit.text = "Вернуться в меню"
        self.ids.btn_submit.disabled = False
        self.ids.btn_abort.opacity = 0
        self.ids.btn_abort.disabled = True

    def show_results(self):
        """Вызывается при успешном прохождении всех вопросов теста с полной очисткой экрана."""
        Window.fullscreen = False
        Clock.unschedule(self.update_question_timer)
        Clock.unschedule(self.update_delay_timer)

        # Полностью стираем верхний статус-бар и таймер времени, которые вам не нужны
        self.status_text = ""
        self.timer_text = ""

        # Стираем контент слайдера и вариантов ответов
        self.ids.options_box.clear_widgets()
        self.ids.slider_container.size_hint_y = None
        self.ids.slider_container.height = 0
        self.ids.img_display.source = ""
        self.image_counter_text = ""

        # Жёстко скрываем стрелочки навигации картинок
        self.ids.slider_nav_bar.opacity = 0
        self.ids.slider_nav_bar.disabled = True
        self.ids.slider_nav_bar.height = 0

        # Выводим финальную статистику СТРОГО по центру экрана
        self.question_text = f"🏆 ТЕСТ УСПЕШНО ЗАВЕРШЕН!\n\nПравильных ответов: {self.score} из {len(self.questions)}\nДопущено ошибок: {self.errors_made}/{self.config['max_errors']}"

        # Перестраиваем кнопки для выхода
        self.ids.btn_submit.text = "Вернуться в меню"
        self.ids.btn_submit.disabled = False
        self.ids.btn_abort.opacity = 0
        self.ids.btn_abort.disabled = True

    def click_ads(self):
        if self.ad_text:
            webbrowser.open(self.target_link)

    def force_exit(self):
        """Прерывает тест и сбрасывает все игровые циклы."""
        Window.fullscreen = False
        Clock.unschedule(self.update_delay_timer)
        Clock.unschedule(self.update_question_timer)
        MDApp.get_running_app().root.current = "test_management"
        # Очищаем временный кэш картинок при выходе в меню
        try:
            temp_cache_dir = os.path.join(get_secure_dir(), ".runtime_media_cache")
            if os.path.exists(temp_cache_dir):
                import shutil
                shutil.rmtree(temp_cache_dir)
        except:
            pass



class QuizWizardScreen(Screen):
    """Полноценный интерактивный конструктор тестов (заменяет Шаги 1, 2 и 3 конструктора Tkinter)."""
    test_name = StringProperty("")
    questions_list = ListProperty([])
    correct_inputs = ListProperty([])
    incorrect_inputs = ListProperty([])
    attached_media = ListProperty([])
    desktop_path = StringProperty("")

    def on_enter(self):
        """Срабатывает при входе в конструктор. Начинаем слушать клавиатуру ПК."""
        Window.bind(on_key_down=self.handle_keyboard_shortcuts)

    def on_leave(self):
        """Срабатывает при выходе из конструктора. Обязательно отключаем слушатель,
        чтобы клавиши Enter/Esc не срабатывали случайно в самом тесте или других меню!"""
        Window.unbind(on_key_down=self.handle_keyboard_shortcuts)

    def handle_keyboard_shortcuts(self, window, key, scancode, codepoint, modifiers):
        """Перехватывает нажатия клавиш Enter и Escape на ПК."""
        # Проверяем, что мы находимся именно на самом первом шаге (ввод названия теста)
        if self.ids.wizard_manager.current == "step_init":

            # Клавиша ENTER (код 40 в Kivy для обычной клавиатуры или 13)
            if key in (13, 40):
                self.start_new_test()
                return True  # Возвращаем True, чтобы Kivy понял, что кнопка обработана

            # Клавиша ESCAPE (код 27)
            elif key == 27:
                self.exit_wizard()
                return True

        return False

    def start_new_test(self):
        """Шаг 1: Инициализация нового теста с полной очисткой старых медиа-данных."""
        name = self.ids.entry_test_name.text.strip()
        if not name:
            MDApp.get_running_app().show_snack("Введите название теста!", is_error=True)
            return

        self.test_name = name
        self.questions_list = []

        # --- ОЧИЩАЕМ СТАРЫЕ КАРТИНКИ ПРИ СТАРТЕ НОВОГО ТЕСТА ---
        self.attached_media = []

        self.ids.wizard_manager.current = "step_questions_list"

    def refresh_questions_list_ui(self):
        """Шаг 2: Обновление нативного прокручиваемого списка добавленных вопросов."""
        from kivymd.uix.list import TwoLineAvatarIconListItem, IconLeftWidget, IconRightWidget
        self.ids.wizard_container.clear_widgets()
        for idx, q in enumerate(self.questions_list):
            item = TwoLineAvatarIconListItem(
                text=f"№ {idx + 1}: {q['question_text']}",
                secondary_text=f"Правильных: {len(q['correct_answers'])} | Неправильных: {len(q['incorrect_answers'])}"
            )
            item.add_widget(IconLeftWidget(icon="help-circle-outline"))

            btn_del = IconRightWidget(icon="close-circle-outline", theme_text_color="Custom",
                                      text_color=(0.9, 0.3, 0.3, 1))
            btn_del.bind(on_release=lambda x, i=idx: self.delete_question_from_list(i))
            item.add_widget(btn_del)

            self.ids.wizard_container.add_widget(item)

    def delete_question_from_list(self, idx):
        del self.questions_list[idx]
        self.refresh_questions_list_ui()
        MDApp.get_running_app().show_snack("Вопрос удален из памяти.")

    def open_question_form(self):
        """Шаг 3: Открытие формы настройки полей ввода одного вопроса с полной очисткой."""
        self.ids.entry_q_text.text = ""
        self.ids.correct_fields_box.clear_widgets()
        self.ids.incorrect_fields_box.clear_widgets()
        self.correct_inputs = []
        self.incorrect_inputs = []

        # --- СБРАСЫВАЕМ ДАННЫЕ КАРТИНКИ ДЛЯ НОВОГО ВОПРОСА ---
        self.attached_media = []

        # Проверяем, существует ли поле ввода на экране, и очищаем его
        if 'entry_pc_media_name' in self.ids:
            self.ids.entry_pc_media_name.text = ""

        # Возвращаем исходный текст кнопке прикрепления
        if 'btn_pc_attach' in self.ids:
            self.ids.btn_pc_attach.text = "📎 Прикрепить"

        self.add_dynamic_reply_field(is_correct=True)
        self.add_dynamic_reply_field(is_correct=False)
        self.ids.wizard_manager.current = "step_question_form"
        # Добавьте эту строчку в конец метода open_question_form()
        if 'thumbnails_container' in self.ids:
            self.ids.thumbnails_container.clear_widgets()

    def add_dynamic_reply_field(self, is_correct=True, text=""):
        """Динамически добавляет строки ввода вариантов ответов с кнопкой удаления."""
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDIconButton

        row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="50dp", spacing="10dp")
        field = MDTextField(
            text=text,
            hint_text="Вариант правильного ответа" if is_correct else "Вариант неправильного ответа",
            mode="line"
        )
        btn_remove = MDIconButton(icon="close", theme_text_color="Custom", text_color=(0.9, 0.3, 0.3, 1))

        row.add_widget(field)
        row.add_widget(btn_remove)

        if is_correct:
            self.ids.correct_fields_box.add_widget(row)
            self.correct_inputs.append(field)
            btn_remove.bind(on_release=lambda x: self.remove_dynamic_reply_field(row, field, self.correct_inputs))
        else:
            self.ids.incorrect_fields_box.add_widget(row)
            self.incorrect_inputs.append(field)
            btn_remove.bind(on_release=lambda x: self.remove_dynamic_reply_field(row, field, self.incorrect_inputs))

    def remove_dynamic_reply_field(self, row_widget, field_obj, target_list):
        if len(target_list) <= 1:
            MDApp.get_running_app().show_snack("Должен остаться хотя бы один вариант ответа!", is_error=True)
            return
        target_list.remove(field_obj)
        row_widget.parent.remove_widget(row_widget)

    def save_question_to_memory(self):
        """Валидирует форму Шага 3 и переносит данные в локальный массив вопросов."""
        q_text = self.ids.entry_q_text.text.strip()
        corrects = [f.text.strip() for f in self.correct_inputs if f.text.strip()]
        incorrects = [f.text.strip() for f in self.incorrect_inputs if f.text.strip()]

        if not q_text:
            MDApp.get_running_app().show_snack("Введите текст вопроса!", is_error=True)
            return
        if not corrects:
            MDApp.get_running_app().show_snack("Заполните хотя бы один правильный ответ!", is_error=True)
            return
        if not incorrects:
            MDApp.get_running_app().show_snack("Заполните хотя бы один неправильный ответ!", is_error=True)
            return
        if len(corrects) != len(set(corrects)) or len(incorrects) != len(set(incorrects)):
            MDApp.get_running_app().show_snack("Обнаружены дубликаты среди вариантов ответов!", is_error=True)
            return
        if set(corrects).intersection(set(incorrects)):
            MDApp.get_running_app().show_snack("Вариант не может быть одновременно правильным и неправильным!",
                                               is_error=True)
            return

        question_data = {
            "question_text": q_text,
            "correct_answers": corrects,
            "incorrect_answers": incorrects,
            # --- ИЗМЕНИТЕ СТРОКУ НИЖЕ ---
            "media_files": list(self.attached_media)
        }


        self.questions_list.append(question_data)
        self.ids.wizard_manager.current = "step_questions_list"
        self.refresh_questions_list_ui()
        MDApp.get_running_app().show_snack("Вопрос успешно зафиксирован в памяти!")

    def save_entire_test_to_json(self):
        """Шаг 2: Финальный экспорт всех вопросов в JSON-файл с автопереименованием и возвратом в меню."""
        if not self.questions_list:
            MDApp.get_running_app().show_snack("Добавьте хотя бы один вопрос перед сохранением теста!", is_error=True)
            return

        target_dir = get_secure_dir()
        base_name = self.test_name.strip()
        final_test_name = base_name

        # Генерируем уникальное имя файла, если такое уже существует на диске
        filename = os.path.join(target_dir, f"{final_test_name}.json")
        counter = 2

        while os.path.exists(filename):
            final_test_name = f"{base_name}({counter})"
            filename = os.path.join(target_dir, f"{final_test_name}.json")
            counter += 1

        try:
            # Записываем JSON-файл
            with open(filename, "w", encoding="utf-8") as f:
                json.dump({
                    "test_name": final_test_name,
                    "questions": list(self.questions_list)
                }, f, ensure_ascii=False, indent=4)

            MDApp.get_running_app().show_snack(f"Тест '{final_test_name}' успешно сохранен!")

            # --- ИСПРАВЛЕНИЕ ТУТ (ДОБАВЛЕН ИНДЕКС) ---
            # Безопасный сброс внутреннего экрана конструктора на Шаг 1
            if self.ids.wizard_manager.screen_names:
                self.ids.wizard_manager.current = self.ids.wizard_manager.screen_names[0]

            # Вызываем функцию закрытия конструктора и перехода на главный экран панели инструментов
            self.exit_wizard()
        except Exception as e:
            MDApp.get_running_app().show_snack(f"Ошибка записи файла: {e}", is_error=True)

    def cancel_wizard_check(self):
        """Проверяет, есть ли вопросы в памяти, и вызывает диалог подтверждения отмены."""
        if not self.questions_list:
            # Если список пуст, выходим сразу без лишних вопросов
            self.exit_wizard()
            return

        # --- ДОБАВЛЯЕМ ОБЯЗАТЕЛЬНЫЕ ЛОКАЛЬНЫЕ ИМПОРТЫ СЮДА ---
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        self.dialog = MDDialog(
            title="Выйти из конструктора?",
            text="Все незафиксированные изменения будут безвозвратно утеряны.",
            buttons=[
                MDFlatButton(
                    text="ОТМЕНА",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDFlatButton(
                    text="ВЫЙТИ",
                    theme_text_color="Custom",
                    text_color=(0.9, 0.2, 0.2, 1),
                    on_release=lambda x: [self.dialog.dismiss(), self.exit_wizard()]
                ),
            ],
        )
        self.dialog.open()


    def exit_wizard(self):
        """Полностью очищает данные и графический список конструктора."""
        if 'entry_test_name' in self.ids:
            self.ids.entry_test_name.text = ""

        self.test_name = ""
        self.questions_list = []
        self.attached_media = []

        # --- ЖЕСТКАЯ ОЧИСТКА ГРАФИЧЕСКОГО ИНТЕРФЕЙСА СПИСКА ---
        # Очищаем виджеты на экране Kivy, чтобы старые вопросы стерлись визуально
        if hasattr(self.ids, 'wizard_container'):
            self.ids.wizard_container.clear_widgets()

        # Переключаем внутренний менеджер на первый экран из списка (ввод названия)
        if hasattr(self.ids, 'wizard_manager') and self.ids.wizard_manager.screen_names:
            self.ids.wizard_manager.current = self.ids.wizard_manager.screen_names[0]

        # Переключаем главный экран приложения на панель инструментов
        MDApp.get_running_app().root.current = "test_management"

    def attach_media_via_plyer(self):
        """Открывает нативный системный проводник Windows для выбора фото и кодирует его в Base64."""
        try:
            # Используем встроенный в KivyMD/Kivy или Tkinter легкий диалог (без вылетов видеокарты)
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()  # Скрываем пустое окно tkinter
            root.attributes("-topmost", True)  # Выводим проводник поверх окон Kivy

            file_path = filedialog.askopenfilename(
                title="Выберите изображение для вопроса",
                filetypes=[("Изображения", "*.jpg *.jpeg *.png *.bmp")]
            )

            if not file_path:
                return  # Пользователь закрыл проводник

            # Проверяем размер файла (ограничение 5 МБ, чтобы JSON не стал слишком тяжелым)
            if os.path.getsize(file_path) > 5 * 1024 * 1024:
                MDApp.get_running_app().show_snack("Файл слишком большой! Выберите фото до 5 МБ.", is_error=True)
                return

            # Читаем картинку и превращаем её в строку Base64
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            # Сохраняем закодированную строку вместо пути к файлу
            # Используем префикс, чтобы игровой движок понял, что это зашитое фото
            b64_data = f"data:image/jpeg;base64,{encoded_string}"

            if b64_data not in self.attached_media:
                self.attached_media.append(b64_data)
                # Выводим имя файла на кнопку
                short_name = os.path.basename(file_path)
                self.ids.btn_pc_attach.text = f"✅ {short_name[:10]}..."
                # Добавьте эту строчку в конец метода attach_media_via_plyer, сразу после self.ids.btn_pc_attach.text = ...
                self.refresh_media_thumbnails_ui()


                MDApp.get_running_app().show_snack("Изображение успешно зашито в вопрос!")

        except Exception as e:
            MDApp.get_running_app().show_snack(f"Ошибка открытия проводника: {e}", is_error=True)

    def process_pc_embedded_file(self):
        """Обрабатывает имя файла без динамической перерисовки графических контейнеров (Защита от 0xC0000005)."""


        # Находим полный путь к файлу в корневой папке программы
        full_path = os.path.abspath(file_name)

        if not os.path.exists(full_path):
            MDApp.get_running_app().show_snack(f"Файл '{file_name}' не найден в папке проекта!", is_error=True)
            return

        # Валидация размера (15 МБ)
        if os.path.getsize(full_path) > 15728640:
            MDApp.get_running_app().show_snack("Файл слишком большой! Ограничение — 15 МБ.", is_error=True)
            return

        # Просто сохраняем путь в массив (видеокарта не задействована, вылет невозможен)
        if full_path not in self.attached_media:
            self.attached_media.append(full_path)

            # Меняем только текст на кнопке, не трогая структуру макета экрана
            self.ids.btn_pc_attach.text = f"✅ Добавлено ({len(self.attached_media)})"
            MDApp.get_running_app().show_snack("Изображение зафиксировано!")

    def handle_mobile_selection(self, selection):
        """Отдельный коллбэк для обработки фото, выбранного в мобильной галерее."""
        if not selection:
            return
        path = selection if isinstance(selection, list) else selection
        if os.path.exists(path) and os.path.getsize(path) > 15728640:
            MDApp.get_running_app().show_snack("Файл слишком большой! Ограничение — 15 МБ.", is_error=True)
            return
        self.attached_media.append(path)

    def refresh_media_thumbnails_ui(self):
        """Динамически генерирует файлы превью, проверяя реальные байты формата (PNG/JPG)."""
        if 'thumbnails_container' not in self.ids:
            return

        self.ids.thumbnails_container.clear_widgets()
        thumb_cache_dir = os.path.join(get_secure_dir(), ".wizard_thumb_cache")

        try:
            if os.path.exists(thumb_cache_dir):
                import shutil
                shutil.rmtree(thumb_cache_dir)
            os.makedirs(thumb_cache_dir, exist_ok=True)
        except:
            os.makedirs(thumb_cache_dir, exist_ok=True)

        from kivymd.uix.boxlayout import MDBoxLayout
        from kivy.uix.image import Image
        from kivymd.uix.button import MDIconButton
        from kivy.cache import Cache

        for idx, media_str in enumerate(list(self.attached_media)):
            media_s = str(media_str).strip()
            if media_s.startswith("data:image"):
                try:
                    if "," in media_s:
                        _, encoded = media_s.split(",", 1)
                    else:
                        encoded = media_s

                    missing_padding = len(encoded) % 4
                    if missing_padding:
                        encoded += '=' * (4 - missing_padding)

                    image_data = base64.b64decode(encoded.encode('utf-8'))

                    # --- ЖЕЛЕЗОБЕТОННАЯ ПРОВЕРКА ПО РЕАЛЬНЫМ БАЙТАМ ФАЙЛА ---
                    ext = "jpg"
                    # Проверяем сигнатуру (первые 4 байта) формата PNG
                    if image_data.startswith(b'\x89PNG'):
                        ext = "png"
                    elif image_data.startswith(b'GIF8'):
                        ext = "gif"

                    timestamp = datetime.datetime.now().microsecond + idx
                    thumb_path = os.path.abspath(os.path.join(thumb_cache_dir, f"thumb_{timestamp}.{ext}"))

                    with open(thumb_path, "wb") as f:
                        f.write(image_data)

                    try:
                        from PIL import Image as PILImage, ImageOps
                        with PILImage.open(thumb_path) as p_img:
                            fixed_img = ImageOps.exif_transpose(p_img)
                            fixed_img.save(thumb_path)
                    except:
                        pass

                    Cache.remove('kv.image', thumb_path)
                    Cache.remove('kv.texture', thumb_path)

                    img_layout = MDBoxLayout(
                        orientation="vertical",
                        size_hint=(None, None),
                        size=("60dp", "60dp"),
                        pos_hint={"center_y": 0.5}
                    )

                    preview_img = Image(
                        source=thumb_path,
                        nocache=True,
                        allow_stretch=True,
                        keep_ratio=True,
                        size_hint=(1, 0.7)
                    )

                    btn_delete = MDIconButton(
                        icon="close-circle",
                        icon_size="16sp",
                        theme_text_color="Custom",
                        text_color=(0.9, 0.2, 0.2, 1),
                        size_hint=(1, 0.3),
                        pos_hint={"center_x": 0.5},
                        on_release=lambda x, m_item=media_str: self.remove_attached_photo(m_item)
                    )

                    img_layout.add_widget(preview_img)
                    img_layout.add_widget(btn_delete)
                    self.ids.thumbnails_container.add_widget(img_layout)

                except Exception as e:
                    print(f"[ОШИБКА ПРЕВЬЮ]: {e}")

    def remove_attached_photo(self, media_item):
        """Удаляет выбранное фото из памяти конструктора и обновляет интерфейс миниатюр."""
        if media_item in self.attached_media:
            self.attached_media.remove(media_item)

            # Обновляем текст на главной кнопке прикрепления
            if self.attached_media:
                self.ids.btn_pc_attach.text = f"✅ Добавлено ({len(self.attached_media)})"
            else:
                self.ids.btn_pc_attach.text = "📎 Прикрепить"

            MDApp.get_running_app().show_snack("Изображение удалено из вопроса")
            # Перерисовываем ленту миниатюр, чтобы удаленное фото исчезло
            self.refresh_media_thumbnails_ui()


if __name__ == "__main__":
    QuizApp().run()
