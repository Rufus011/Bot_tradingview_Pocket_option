import sys
import time
import logging
import pygame
import threading
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QTextEdit, QComboBox, QFormLayout, QCheckBox)
from PyQt5.QtGui import QFont
from pocketoptionapi.stable_api import PocketOption
from concurrent.futures import ThreadPoolExecutor
from tradingview_ta import TA_Handler, Interval

# Инициализация pygame mixer
pygame.mixer.init()

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

# Расширенный список символов (валютные пары, акции и т.д.)
Symbol = [
    'Выберите валютную пару', 'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD', 'EURJPY', 'EURGBP', 'GBPJPY',
    'EURAUD', 'AUDJPY', 'CADJPY', 'CHFJPY', 'AUDCAD', 'NZDJPY', 'AUDNZD', 'USDSGD', 'EURCHF', 'EURCAD',
    'GBPCHF', 'GBPAUD', 'NZDCAD', 'USDHKD', 'USDZAR', 'USDTRY', 'USDMXN', 'USDNOK', 'USDSEK', 'USDPLN',
    'EURUSD_otc', 'GBPUSD_otc', 'USDJPY_otc', 'AUDUSD_otc', 'USDCAD_otc', 'USDCHF_otc', 'NZDUSD_otc', 'EURJPY_otc',
    'EURGBP_otc', 'GBPJPY_otc',
    'EURAUD_otc', 'AUDJPY_otc', 'CADJPY_otc', 'CHFJPY_otc', 'AUDCAD_otc', 'NZDJPY_otc', 'AUDNZD_otc', 'USDSGD_otc',
    'EURCHF_otc', 'EURCAD_otc',
    'GBPCHF_otc', 'GBPAUD_otc', 'NZDCAD_otc', 'USDHKD_otc', 'USDZAR_otc', 'USDTRY_otc', 'USDMXN_otc', 'USDNOK_otc',
    'USDSEK_otc', 'USDPLN_otc'
]

def play_sound():
    try:
        pygame.mixer.music.load(r'C:\Users\Rufus\Downloads\race-countdown-beeps-fast-01-sound-effect-4132081.mp3')
        pygame.mixer.music.play()
    except Exception as e:
        logging.error(f"Ошибка воспроизведения звука: {str(e)}")

class ApiWorker(QThread):
    update_signal_result = pyqtSignal(str, object, float)

    def __init__(self, api, selected_symbol, period):
        super().__init__()
        self.api = api
        self.selected_symbol = selected_symbol
        self.period = period

    def run(self):
        try:
            if self.api and self.api.check_connect():
                balance = self.api.get_balance()
                self.update_signal_result.emit(self.selected_symbol, None, balance)
            else:
                self.update_signal_result.emit(self.selected_symbol, None, 0.0)
        except Exception as e:
            self.update_signal_result.emit(self.selected_symbol, None, 0.0)
            logging.error(f"Ошибка обновления сигнала: {str(e)}")

class TradingBotGUI(QMainWindow):
    log_signal = pyqtSignal(str)  # Определение сигнала

    def __init__(self):
        super().__init__()
        self.setWindowTitle("trading bot POCKET OPTION")
        self.setGeometry(100, 100, 1000, 600)
        self.setWindowIcon(QIcon(r"C:\Project.py\pythonProject\PocketOptionAPI\pocket_option.png"))  # Установить иконку
        self.balance_label = QLabel("Баланс: 💵")
        self.balance_label.setFont(QFont("Arial",12))
        self.setup_ui()
        self.timer = None
        self.api = None
        self.period = 60  # Период по умолчанию
        self.api_worker = None
        self.executor = ThreadPoolExecutor(max_workers=5)

        self.log_signal.connect(self.log_text.append)  # Подключение сигнала к логам

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        # Настройки API
        settings_group = QWidget()
        settings_layout = QFormLayout()
        settings_group.setLayout(settings_layout)

        self.demo_ssid_input = QLineEdit()
        settings_layout.addRow("SSID:Demo", self.demo_ssid_input)

        self.real_ssid_input = QLineEdit()
        settings_layout.addRow("SSID:Real", self.real_ssid_input)

        main_layout.addWidget(settings_group)

        # Отображение баланса
        main_layout.addWidget(self.balance_label)

        # Торговый интерфейс
        trading_layout = QHBoxLayout()

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)

        middle_panel = QWidget()
        middle_layout = QVBoxLayout()
        middle_panel.setLayout(middle_layout)

        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)

        trading_layout.addWidget(left_panel)
        trading_layout.addWidget(middle_panel)
        trading_layout.addWidget(right_panel)

        main_layout.addLayout(trading_layout)

        # Добавляем CheckBox для автоматической торговли
        self.auto_trade_checkbox = QCheckBox("Автотрейдинг 🔎")
        left_layout.addWidget(self.auto_trade_checkbox)
        # Добавляем ComboBox для выбора интервала
        self.interval_combo = QComboBox()
        self.interval_combo.addItems([
            "Выберите интервал TradingView", "1m", "5m", "15m", "30m", "1h",
            "2h", "4h", "1d", "1W", "1M"
        ])
        left_layout.addWidget(self.interval_combo)

        self.coin_combo = QComboBox()
        self.coin_combo.addItems(Symbol)
        left_layout.addWidget(self.coin_combo)

        self.trade_input = QLineEdit()
        self.trade_input.setPlaceholderText("Введите сумму сделки")
        left_layout.addWidget(self.trade_input)

        self.expiry_combo = QComboBox()
        self.expiry_combo.addItems(
            ["Выберите время экспирации", "5s", "15s", "30s", "1m", "2m", "3m", "5m", "10m", "15m", "30m", "1h"])
        left_layout.addWidget(self.expiry_combo)

        self.buy_button = QPushButton("Купить")
        self.buy_button.clicked.connect(self.buy)
        left_layout.addWidget(self.buy_button)

        self.sell_button = QPushButton("Продать")
        self.sell_button.clicked.connect(self.sell)
        left_layout.addWidget(self.sell_button)

        # Виджеты правой панели
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        right_layout.addWidget(self.log_text)

        self.start_bot_button = QPushButton("Запустить бота")
        self.start_bot_button.clicked.connect(self.start_bot)
        right_layout.addWidget(self.start_bot_button)

        self.stop_bot_button = QPushButton("Остановить бота")
        self.stop_bot_button.clicked.connect(self.stop_bot)
        right_layout.addWidget(self.stop_bot_button)

    def start_timer(self):
        if self.timer is None:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_signal)
            self.timer.start(5000)  # Обновление каждые 5 секунд
            self.log_text.append("Таймер запущен")

    def stop_timer(self):
        if self.timer is not None:
            self.timer.stop()
            self.timer = None
            self.log_text.append("Таймер остановлен")

    def get_expirations(self):
        selected_expirations = self.expiry_combo.currentText()
        if selected_expirations == "5s":
            return 5
        elif selected_expirations == "15s":
            return 15
        elif selected_expirations == "30s":
            return 30
        elif selected_expirations == "1m":
            return 60
        elif selected_expirations == "2m":
            return 120
        elif selected_expirations == "3m":
            return 180
        elif selected_expirations == "5m":
            return 300
        elif selected_expirations == "10m":
            return 600
        elif selected_expirations == "15m":
            return 900
        elif selected_expirations == "30m":
            return 1800
        elif selected_expirations == "1h":
            return 3600
        return 60  # Значение по умолчанию

    def buy(self):
        self.executor.submit(self._buy, 'call')

    def sell(self):
        self.executor.submit(self._buy, 'put')

    def _buy(self, action, symbol=None):
        try:
            if not self.api or not self.api.check_connect():
                self.log_signal.emit("Нет подключения к API")
                return

            asset = symbol or self.coin_combo.currentText()
            amount_text = self.trade_input.text()
            if not amount_text:
                self.log_signal.emit("Сумма сделки не указана")
                return

            try:
                amount = float(amount_text)
            except ValueError:
                self.log_signal.emit("Некорректная сумма сделки")
                return

            duration = self.get_expirations()

            try:
                buy_info = self.api.buy(amount=amount, active=asset, expirations=duration, action=action)
                if not isinstance(buy_info, dict):
                    return
            except Exception as e:
                self.log_signal.emit(f"{action.capitalize()}: (False, None) не достаточно средств")
                return

            time.sleep(duration + 5)

            try:
                result = self.api.check_win(buy_info["id"])
                if not isinstance(result, dict):
                    self.log_signal.emit(f"Ошибка при {action}: result не является словарем")
                    return
                self.log_signal.emit(f"Результат: {result}")
            except KeyError:
                self.log_signal.emit(f"Ошибка при {action}: 'id' отсутствует в buy_info")
                return

            new_balance = self.api.get_balance()
            self.log_signal.emit(f"Новый баланс: {new_balance}")

        except Exception as e:
            self.log_signal.emit(f"Ошибка при {action}: {str(e)}")

    def start_bot(self):
        try:
            demo_ssid = self.demo_ssid_input.text()
            real_ssid = self.real_ssid_input.text()
            if demo_ssid and '"isDemo":1' in demo_ssid:
                self.log_text.append(f"Бот запущен с Demo SSID: {demo_ssid}")
                ssid = demo_ssid
            elif real_ssid and '"isDemo":0' in real_ssid:
                self.log_text.append(f"Бот запущен с Real SSID: {real_ssid}")
                ssid = real_ssid
            else:
                self.log_text.append("Невалидный SSID или параметр isDemo")
                return

            self.api = PocketOption(ssid)
            self.api.connect()
            time.sleep(5)
            if self.api.check_connect():
                self.log_text.append("Подключение к PocketOption API успешно")
                self.start_timer()
                self.update_signal()  # Немедленный вызов обновления сигнала после запуска

                if self.auto_trade_checkbox.isChecked():
                    self.trading_thread = threading.Thread(target=self.trading_loop)
                    self.trading_thread.start()

            else:
                self.log_text.append("Не удалось подключиться к PocketOption API")

        except Exception as e:
            self.log_text.append(f"Ошибка запуска бота: {str(e)}")

    def stop_bot(self):
        self.stop_timer()
        self.log_text.append("Бот остановлен")
        if self.api and self.api.check_connect():
            self.api.disconnect()

    def update_signal(self):
        selected_symbol = self.coin_combo.currentText()
        self.api_worker = ApiWorker(self.api, selected_symbol, self.period)
        self.api_worker.update_signal_result.connect(self.handle_api_response)
        self.api_worker.start()

    @pyqtSlot(str, object, float)
    def handle_api_response(self, selected_symbol, candles, balance):
        self.log_text.clear()  # Очистка предыдущих сообщений
        self.log_text.append(f"📶{selected_symbol}")
        self.balance_label.setText(f"Баланс:💵{balance}")
        self.log_text.append(f"Баланс:💵{balance}")

    def trading_loop(self):
        while self.auto_trade_checkbox.isChecked():
            self.log_text.append('===================ПОИСК СИГНАЛА====================')
            for symbol in Symbol:
                if symbol == 'Выберите валютную пару':
                    continue
                try:
                    data = self.get_tradingview_data(symbol)
                    if data['RECOMMENDATION'] == 'STRONG_BUY':
                        self.log_text.append(f"{symbol} Buy")
                        self._buy('call', symbol)
                    elif data['RECOMMENDATION'] == 'STRONG_SELL':
                        self.log_text.append(f"{symbol} Sell")
                        self._buy('put', symbol)
                    time.sleep(1)
                except Exception as e:
                    self.log_text.append(f"Ошибка получения данных для {symbol}: {str(e)}")

    def get_tradingview_data(self, symbol):
        interval = self.get_tradingview_interval()
        handler = TA_Handler(
            symbol=symbol,
            screener="forex",
            exchange="FX_IDC",
            interval=interval
        )
        return handler.get_analysis().summary

    def get_tradingview_interval(self):
        interval_map = {
            "Выберите интервал TradingView": Interval.INTERVAL_1_HOUR,  # Значение по умолчанию
            "1m": Interval.INTERVAL_1_MINUTE,
            "5m": Interval.INTERVAL_5_MINUTES,
            "15m": Interval.INTERVAL_15_MINUTES,
            "30m": Interval.INTERVAL_30_MINUTES,
            "1h": Interval.INTERVAL_1_HOUR,
            "2h": Interval.INTERVAL_2_HOURS,
            "4h": Interval.INTERVAL_4_HOURS,
            "1d": Interval.INTERVAL_1_DAY,
            "1W": Interval.INTERVAL_1_WEEK,
            "1M": Interval.INTERVAL_1_MONTH
        }
        selected_interval = self.interval_combo.currentText()
        return interval_map.get(selected_interval, Interval.INTERVAL_1_HOUR)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        window = TradingBotGUI()
        window.setStyleSheet("""
                QMainWindow {
                    background-color: #2c3e50; /* Цвет фона главного окна */
                    color: #ecf0f1; /* Цвет текста по умолчанию */
                }
                QLabel, QTextEdit {
                    color: #ecf0f1; /* Цвет текста для QLabel и QTextEdit */
                    font-size: 12px; /* Размер шрифта для лучшей читаемости */
                }
                QPushButton {
                    background-color: #3498db; /* Цвет фона для QPushButton */
                    color: white; /* Цвет текста для QPushButton */
                    border: none; /* Без границ для QPushButton */
                    padding: 8px 12px; /* Уменьшенный отступ для QPushButton */
                    border-radius: 3px; /* Закругленные углы для QPushButton */
                    font-size: 12px; /* Размер шрифта для лучшей читаемости */
                }
                QPushButton:hover {
                    background-color: #2980b9; /* Цвет фона для QPushButton при наведении */
                }
                QLineEdit, QComboBox {
                    background-color: #34495e; /* Цвет фона для QLineEdit и QComboBox */
                    color: #ecf0f1; /* Цвет текста для QLineEdit и QComboBox */
                    border: 1px solid #7f8c8d; /* Цвет границы для QLineEdit и QComboBox */
                    padding: 5px; /* Увеличенный отступ для QLineEdit и QComboBox */
                    font-size: 12px; /* Размер шрифта для лучшей читаемости */
                }
                QTextEdit {
                    background-color: #2c3e50; /* Цвет фона для QTextEdit */
                    color: #ecf0f1; /* Цвет текста для QTextEdit */
                    font-size: 12px; /* Размер шрифта для лучшей читаемости */
                }
            """)
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
        sys.exit(1)





























































