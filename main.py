from owlready2 import *
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, messagebox
import random
import threading
import time
from datetime import datetime


class VentilationOntology:
    """Онтология системы вентиляции промышленного цеха"""

    def __init__(self, filepath="ventilation_ontology.rdf"):
        self.filepath = filepath
        self.onto = self._create_ontology()

    def _create_ontology(self):
        """Создание онтологии предметной области"""
        onto = get_ontology("http://www.example.org/ventilation#")

        with onto:
            # Классы
            class Workshop(Thing): pass

            class VentilationSystem(Thing): pass

            class Sensor(Thing): pass

            class Actuator(Thing): pass

            class Rule(Thing): pass

            class EnvironmentalCondition(Thing): pass

            # Объектные свойства
            class hasSensor(Workshop >> Sensor): pass

            class hasActuator(VentilationSystem >> Actuator): pass

            class hasRule(VentilationSystem >> Rule): pass

            class monitors(Sensor >> EnvironmentalCondition): pass

            # Свойства данных
            class hasTemperature(Sensor >> float, FunctionalProperty): pass

            class hasHumidity(Sensor >> float, FunctionalProperty): pass

            class hasCO2(Sensor >> float, FunctionalProperty): pass

            class hasAirflow(Actuator >> float, FunctionalProperty): pass

            class hasPriority(Rule >> int, FunctionalProperty): pass

            class hasFanSpeed(VentilationSystem >> float, FunctionalProperty): pass

            class hasHeaterPower(VentilationSystem >> float, FunctionalProperty): pass

            class hasCoolerPower(VentilationSystem >> float, FunctionalProperty): pass

            class hasHumidifierPower(VentilationSystem >> float, FunctionalProperty): pass

        return onto

    def initialize_state(self):
        """Инициализация начального состояния"""
        # Создаем индивидов (если их нет)
        if not hasattr(self, 'workshop'):
            self.workshop = self.onto.Workshop("MainWorkshop")
            self.ventilation = self.onto.VentilationSystem("MainVentilation")
            self.temp_sensor = self.onto.Sensor("TemperatureSensor")
            self.humidity_sensor = self.onto.Sensor("HumiditySensor")
            self.co2_sensor = self.onto.Sensor("CO2Sensor")

            # Начальные значения (явно преобразуем в float)
            self.temp_sensor.hasTemperature = 22.0
            self.humidity_sensor.hasHumidity = 50.0
            self.co2_sensor.hasCO2 = 400.0

            self.ventilation.hasFanSpeed = 50.0
            self.ventilation.hasHeaterPower = 0.0
            self.ventilation.hasCoolerPower = 0.0
            self.ventilation.hasHumidifierPower = 0.0

            # Связи
            self.workshop.hasSensor = [self.temp_sensor, self.humidity_sensor, self.co2_sensor]

            self.save_ontology()

    def get_state(self):
        """Получение текущего состояния системы"""
        return {
            'temperature': self.temp_sensor.hasTemperature if hasattr(self,
                                                                      'temp_sensor') and self.temp_sensor.hasTemperature else 22.0,
            'humidity': self.humidity_sensor.hasHumidity if hasattr(self,
                                                                    'humidity_sensor') and self.humidity_sensor.hasHumidity else 50.0,
            'co2': self.co2_sensor.hasCO2 if hasattr(self, 'co2_sensor') and self.co2_sensor.hasCO2 else 400.0,
            'fan_speed': self.ventilation.hasFanSpeed if hasattr(self,
                                                                 'ventilation') and self.ventilation.hasFanSpeed else 50.0,
            'heater_power': self.ventilation.hasHeaterPower if hasattr(self,
                                                                       'ventilation') and self.ventilation.hasHeaterPower else 0.0,
            'cooler_power': self.ventilation.hasCoolerPower if hasattr(self,
                                                                       'ventilation') and self.ventilation.hasCoolerPower else 0.0,
            'humidifier_power': self.ventilation.hasHumidifierPower if hasattr(self,
                                                                               'ventilation') and self.ventilation.hasHumidifierPower else 0.0
        }

    def update_sensors(self, temperature, humidity, co2):
        """Обновление показаний датчиков"""
        if hasattr(self, 'temp_sensor'):
            # Преобразуем numpy типы в стандартные Python float
            self.temp_sensor.hasTemperature = float(temperature)
            self.humidity_sensor.hasHumidity = float(humidity)
            self.co2_sensor.hasCO2 = float(co2)
            self.save_ontology()

    def update_actuators(self, fan_speed, heater_power, cooler_power, humidifier_power):
        """Обновление состояния исполнительных устройств"""
        if hasattr(self, 'ventilation'):
            # Преобразуем numpy типы в стандартные Python float
            self.ventilation.hasFanSpeed = float(fan_speed)
            self.ventilation.hasHeaterPower = float(heater_power)
            self.ventilation.hasCoolerPower = float(cooler_power)
            self.ventilation.hasHumidifierPower = float(humidifier_power)
            self.save_ontology()

    def save_ontology(self):
        """Сохранение онтологии в файл"""
        try:
            self.onto.save(file=self.filepath, format="rdfxml")
        except:
            pass


class FuzzyController:
    """Нечеткий контроллер для системы вентиляции"""

    def __init__(self):
        # Универсумы для входных переменных
        self.universe_temp = np.arange(0, 51, 0.5)  # Температура 0-50°C
        self.universe_humidity = np.arange(0, 101, 1)  # Влажность 0-100%
        self.universe_co2 = np.arange(0, 2001, 10)  # CO2 0-2000 ppm
        self.universe_fan = np.arange(0, 101, 1)  # Скорость вентилятора 0-100%
        self.universe_heater = np.arange(0, 101, 1)  # Мощность нагревателя 0-100%
        self.universe_cooler = np.arange(0, 101, 1)  # Мощность охладителя 0-100%
        self.universe_humidifier = np.arange(0, 101, 1)  # Мощность увлажнителя 0-100%

        # Входные переменные
        self.temperature = ctrl.Antecedent(self.universe_temp, 'temperature')
        self.humidity = ctrl.Antecedent(self.universe_humidity, 'humidity')
        self.co2 = ctrl.Antecedent(self.universe_co2, 'co2')

        # Выходные переменные
        self.fan_speed = ctrl.Consequent(self.universe_fan, 'fan_speed')
        self.heater_power = ctrl.Consequent(self.universe_heater, 'heater_power')
        self.cooler_power = ctrl.Consequent(self.universe_cooler, 'cooler_power')
        self.humidifier_power = ctrl.Consequent(self.universe_humidifier, 'humidifier_power')

        # Функции принадлежности для температуры
        self.temperature['very_cold'] = fuzz.trimf(self.universe_temp, [0, 0, 10])
        self.temperature['cold'] = fuzz.trimf(self.universe_temp, [5, 12, 18])
        self.temperature['normal'] = fuzz.trimf(self.universe_temp, [16, 22, 26])
        self.temperature['warm'] = fuzz.trimf(self.universe_temp, [23, 28, 33])
        self.temperature['hot'] = fuzz.trimf(self.universe_temp, [30, 40, 50])

        # Функции принадлежности для влажности
        self.humidity['very_dry'] = fuzz.trimf(self.universe_humidity, [0, 0, 20])
        self.humidity['dry'] = fuzz.trimf(self.universe_humidity, [15, 30, 45])
        self.humidity['optimal'] = fuzz.trimf(self.universe_humidity, [40, 50, 60])
        self.humidity['humid'] = fuzz.trimf(self.universe_humidity, [55, 70, 85])
        self.humidity['very_humid'] = fuzz.trimf(self.universe_humidity, [80, 90, 100])

        # Функции принадлежности для CO2
        self.co2['low'] = fuzz.trimf(self.universe_co2, [0, 0, 400])
        self.co2['normal'] = fuzz.trimf(self.universe_co2, [300, 500, 800])
        self.co2['elevated'] = fuzz.trimf(self.universe_co2, [600, 1000, 1500])
        self.co2['high'] = fuzz.trimf(self.universe_co2, [1200, 1600, 2000])

        # Функции принадлежности для выходных переменных
        self.fan_speed['off'] = fuzz.trimf(self.universe_fan, [0, 0, 10])
        self.fan_speed['low'] = fuzz.trimf(self.universe_fan, [5, 25, 45])
        self.fan_speed['medium'] = fuzz.trimf(self.universe_fan, [35, 50, 65])
        self.fan_speed['high'] = fuzz.trimf(self.universe_fan, [55, 75, 95])
        self.fan_speed['maximum'] = fuzz.trimf(self.universe_fan, [85, 100, 100])

        self.heater_power['off'] = fuzz.trimf(self.universe_heater, [0, 0, 10])
        self.heater_power['low'] = fuzz.trimf(self.universe_heater, [5, 30, 50])
        self.heater_power['high'] = fuzz.trimf(self.universe_heater, [40, 75, 100])

        self.cooler_power['off'] = fuzz.trimf(self.universe_cooler, [0, 0, 10])
        self.cooler_power['low'] = fuzz.trimf(self.universe_cooler, [5, 30, 50])
        self.cooler_power['high'] = fuzz.trimf(self.universe_cooler, [40, 75, 100])

        self.humidifier_power['off'] = fuzz.trimf(self.universe_humidifier, [0, 0, 10])
        self.humidifier_power['low'] = fuzz.trimf(self.universe_humidifier, [5, 30, 50])
        self.humidifier_power['high'] = fuzz.trimf(self.universe_humidifier, [40, 75, 100])

        # Правила управления температурой
        rule1 = ctrl.Rule(self.temperature['very_cold'],
                          (self.heater_power['high'], self.fan_speed['low']))
        rule2 = ctrl.Rule(self.temperature['cold'],
                          (self.heater_power['low'], self.fan_speed['low']))
        rule3 = ctrl.Rule(self.temperature['normal'],
                          (self.heater_power['off'], self.cooler_power['off'], self.fan_speed['medium']))
        rule4 = ctrl.Rule(self.temperature['warm'],
                          (self.cooler_power['low'], self.fan_speed['medium']))
        rule5 = ctrl.Rule(self.temperature['hot'],
                          (self.cooler_power['high'], self.fan_speed['high']))

        # Правила управления влажностью
        rule6 = ctrl.Rule(self.humidity['very_dry'],
                          (self.humidifier_power['high'], self.fan_speed['low']))
        rule7 = ctrl.Rule(self.humidity['dry'],
                          (self.humidifier_power['low'], self.fan_speed['low']))
        rule8 = ctrl.Rule(self.humidity['optimal'],
                          (self.humidifier_power['off'], self.fan_speed['medium']))
        rule9 = ctrl.Rule(self.humidity['humid'],
                          (self.fan_speed['high'],))
        rule10 = ctrl.Rule(self.humidity['very_humid'],
                           (self.fan_speed['maximum'],))

        # Правила управления CO2
        rule11 = ctrl.Rule(self.co2['elevated'],
                           (self.fan_speed['high'],))
        rule12 = ctrl.Rule(self.co2['high'],
                           (self.fan_speed['maximum'],))
        rule13 = ctrl.Rule(self.co2['low'] & self.temperature['normal'],
                           (self.fan_speed['low'],))

        # Создание системы управления
        self.control_system = ctrl.ControlSystem([
            rule1, rule2, rule3, rule4, rule5,
            rule6, rule7, rule8, rule9, rule10,
            rule11, rule12, rule13
        ])
        self.controller = ctrl.ControlSystemSimulation(self.control_system)

    def compute(self, temperature, humidity, co2):
        """Вычисление управляющих воздействий"""
        try:
            self.controller.input['temperature'] = temperature
            self.controller.input['humidity'] = humidity
            self.controller.input['co2'] = co2

            self.controller.compute()

            fan_speed = self.controller.output.get('fan_speed', 50.0)
            heater_power = self.controller.output.get('heater_power', 0.0)
            cooler_power = self.controller.output.get('cooler_power', 0.0)
            humidifier_power = self.controller.output.get('humidifier_power', 0.0)

            return {
                'fan_speed': max(0, min(100, fan_speed)),
                'heater_power': max(0, min(100, heater_power)),
                'cooler_power': max(0, min(100, cooler_power)),
                'humidifier_power': max(0, min(100, humidifier_power))
            }
        except:
            return {
                'fan_speed': 50.0,
                'heater_power': 0.0,
                'cooler_power': 0.0,
                'humidifier_power': 0.0
            }


class WorkshopSimulator:
    """Симулятор промышленного цеха"""

    def __init__(self):
        self.external_temp = 15.0  # Наружная температура
        self.external_humidity = 60.0  # Наружная влажность
        self.heat_generation = 0.0  # Тепловыделение от оборудования
        self.humidity_generation = 0.0  # Влаговыделение
        self.co2_generation = 0.0  # Выделение CO2
        self.workers_count = 10  # Количество рабочих

        # Состояние окружающей среды через время
        self.time_of_day = 0  # 0-23 часа

    def update_environment(self, dt=1.0):
        """Обновление параметров окружающей среды"""
        # Время суток меняется пропорционально dt
        self.time_of_day = (self.time_of_day + dt / 3600) % 24

        hour_angle = (self.time_of_day - 6) * np.pi / 12
        self.external_temp = 15.0 + 10.0 * np.sin(hour_angle)
        self.external_humidity = 60.0 + 20.0 * np.cos(hour_angle)

        # Генерация тепла/CO2 - меняем плавно, без резких скачков
        # Используем dt для плавного перехода между значениями
        target_heat = 0
        target_co2 = 0

        if 8 <= self.time_of_day <= 18:
            target_heat = random.uniform(5.0, 15.0)
            target_co2 = random.uniform(100, 500) * self.workers_count / 10
        else:
            target_heat = random.uniform(1.0, 5.0)
            target_co2 = random.uniform(50, 150) * self.workers_count / 20

        # Плавное изменение (не более чем на 0.5 в секунду модельного времени)
        max_change_per_sec = 0.5
        if abs(target_heat - self.heat_generation) < max_change_per_sec * dt:
            self.heat_generation = target_heat
        else:
            self.heat_generation += max_change_per_sec * dt * (1 if target_heat > self.heat_generation else -1)

        if abs(target_co2 - self.co2_generation) < max_change_per_sec * dt * 50:
            self.co2_generation = target_co2
        else:
            self.co2_generation += max_change_per_sec * dt * 50 * (1 if target_co2 > self.co2_generation else -1)

        self.humidity_generation = random.uniform(0.0, 5.0)

    def calculate_changes(self, current_temp, current_humidity, current_co2,
                          fan_speed, heater_power, cooler_power, humidifier_power, dt=1.0):
        """Расчет изменений параметров в цехе"""

        # Влияние вентиляции (воздухообмен)
        ventilation_rate = fan_speed / 100.0 * 0.1  # Коэффициент воздухообмена

        # Изменение температуры
        temp_diff_outside = (self.external_temp - current_temp) * ventilation_rate
        temp_heater = heater_power / 100.0 * 2.0  # Нагрев
        temp_cooler = -cooler_power / 100.0 * 3.0  # Охлаждение
        temp_equipment = self.heat_generation * 0.1  # Тепло от оборудования

        d_temp = (temp_diff_outside + temp_heater + temp_cooler + temp_equipment) * dt / 60.0

        # Изменение влажности
        humidity_diff_outside = (self.external_humidity - current_humidity) * ventilation_rate
        humidity_humidifier = humidifier_power / 100.0 * 1.5
        humidity_equipment = self.humidity_generation * 0.1

        d_humidity = (humidity_diff_outside + humidity_humidifier + humidity_equipment) * dt / 60.0

        # Изменение CO2
        co2_ventilation = -current_co2 * ventilation_rate * 0.5
        co2_people = self.co2_generation * 0.1

        d_co2 = (co2_ventilation + co2_people) * dt / 60.0

        return d_temp, d_humidity, d_co2


class VentilationGUI:
    """Графический интерфейс системы управления вентиляцией"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Система управления вентиляцией промышленного цеха")
        self.root.geometry("1400x900")

        # Инициализация компонентов
        self.ontology = VentilationOntology()
        self.ontology.initialize_state()
        self.fuzzy_controller = FuzzyController()
        self.simulator = WorkshopSimulator()

        # Переменные состояния
        self.current_temp = 22.0
        self.current_humidity = 50.0
        self.current_co2 = 400.0
        self.fan_speed = 50.0
        self.heater_power = 0.0
        self.cooler_power = 0.0
        self.humidifier_power = 0.0

        # Параметры симуляции
        self.simulation_speed = 1.0  # Множитель скорости
        self.is_running = False
        self.manual_mode = False

        # Данные для графиков
        self.time_history = []
        self.temp_history = []
        self.humidity_history = []
        self.co2_history = []
        self.fan_history = []
        self.heater_history = []
        self.cooler_history = []
        self.humidifier_history = []

        self.max_history = 200  # Максимальное количество точек на графике

        self.setup_gui()
        self.update_display()

    def setup_gui(self):
        """Настройка графического интерфейса"""

        # Главный фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Заголовок
        title_label = ttk.Label(main_frame, text="СИСТЕМА УПРАВЛЕНИЯ ВЕНТИЛЯЦИЕЙ ПРОМЫШЛЕННОГО ЦЕХА",
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)

        # Левая панель - текущие показатели
        left_frame = ttk.LabelFrame(main_frame, text="Текущие показатели", padding="10")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)

        # Датчики
        ttk.Label(left_frame, text="ДАТЧИКИ", font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Label(left_frame, text="Температура:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.temp_label = ttk.Label(left_frame, text="22.0°C", font=('Arial', 11))
        self.temp_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.temp_progress = ttk.Progressbar(left_frame, length=150, mode='determinate', maximum=50)
        self.temp_progress.grid(row=2, column=0, columnspan=2, pady=2)

        ttk.Label(left_frame, text="Влажность:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.humidity_label = ttk.Label(left_frame, text="50.0%", font=('Arial', 11))
        self.humidity_label.grid(row=3, column=1, sticky=tk.W, pady=2)
        self.humidity_progress = ttk.Progressbar(left_frame, length=150, mode='determinate', maximum=100)
        self.humidity_progress.grid(row=4, column=0, columnspan=2, pady=2)

        ttk.Label(left_frame, text="CO₂:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.co2_label = ttk.Label(left_frame, text="400 ppm", font=('Arial', 11))
        self.co2_label.grid(row=5, column=1, sticky=tk.W, pady=2)
        self.co2_progress = ttk.Progressbar(left_frame, length=150, mode='determinate', maximum=2000)
        self.co2_progress.grid(row=6, column=0, columnspan=2, pady=2)

        # Исполнительные устройства
        ttk.Label(left_frame, text="\nИСПОЛНИТЕЛЬНЫЕ УСТРОЙСТВА",
                  font=('Arial', 12, 'bold')).grid(row=7, column=0, columnspan=2, pady=5)

        ttk.Label(left_frame, text="Вентилятор:").grid(row=8, column=0, sticky=tk.W, pady=2)
        self.fan_label = ttk.Label(left_frame, text="50%", font=('Arial', 11))
        self.fan_label.grid(row=8, column=1, sticky=tk.W, pady=2)
        self.fan_progress = ttk.Progressbar(left_frame, length=150, mode='determinate', maximum=100)
        self.fan_progress.grid(row=9, column=0, columnspan=2, pady=2)

        ttk.Label(left_frame, text="Нагреватель:").grid(row=10, column=0, sticky=tk.W, pady=2)
        self.heater_label = ttk.Label(left_frame, text="0%", font=('Arial', 11))
        self.heater_label.grid(row=10, column=1, sticky=tk.W, pady=2)
        self.heater_progress = ttk.Progressbar(left_frame, length=150, mode='determinate', maximum=100)
        self.heater_progress.grid(row=11, column=0, columnspan=2, pady=2)

        ttk.Label(left_frame, text="Охладитель:").grid(row=12, column=0, sticky=tk.W, pady=2)
        self.cooler_label = ttk.Label(left_frame, text="0%", font=('Arial', 11))
        self.cooler_label.grid(row=12, column=1, sticky=tk.W, pady=2)
        self.cooler_progress = ttk.Progressbar(left_frame, length=150, mode='determinate', maximum=100)
        self.cooler_progress.grid(row=13, column=0, columnspan=2, pady=2)

        ttk.Label(left_frame, text="Увлажнитель:").grid(row=14, column=0, sticky=tk.W, pady=2)
        self.humidifier_label = ttk.Label(left_frame, text="0%", font=('Arial', 11))
        self.humidifier_label.grid(row=14, column=1, sticky=tk.W, pady=2)
        self.humidifier_progress = ttk.Progressbar(left_frame, length=150, mode='determinate', maximum=100)
        self.humidifier_progress.grid(row=15, column=0, columnspan=2, pady=2)

        # Внешние условия
        ttk.Label(left_frame, text="\nВНЕШНИЕ УСЛОВИЯ",
                  font=('Arial', 12, 'bold')).grid(row=16, column=0, columnspan=2, pady=5)

        ttk.Label(left_frame, text="Температура снаружи:").grid(row=17, column=0, sticky=tk.W, pady=2)
        self.ext_temp_label = ttk.Label(left_frame, text="15.0°C", font=('Arial', 11))
        self.ext_temp_label.grid(row=17, column=1, sticky=tk.W, pady=2)

        ttk.Label(left_frame, text="Влажность снаружи:").grid(row=18, column=0, sticky=tk.W, pady=2)
        self.ext_humidity_label = ttk.Label(left_frame, text="60.0%", font=('Arial', 11))
        self.ext_humidity_label.grid(row=18, column=1, sticky=tk.W, pady=2)

        ttk.Label(left_frame, text="Время суток:").grid(row=19, column=0, sticky=tk.W, pady=2)
        self.time_label = ttk.Label(left_frame, text="00:00", font=('Arial', 11))
        self.time_label.grid(row=19, column=1, sticky=tk.W, pady=2)

        # Центральная панель - графики
        center_frame = ttk.LabelFrame(main_frame, text="Графики параметров", padding="10")
        center_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)

        # Создание фигуры matplotlib
        self.fig, self.axes = plt.subplots(3, 2, figsize=(10, 8))
        self.fig.tight_layout(pad=3.0)

        # Настройка подграфиков
        titles = ['Температура (°C)', 'Влажность (%)', 'CO₂ (ppm)',
                  'Скорость вентилятора (%)', 'Мощность нагревателя (%)', 'Мощность охладителя (%)']
        colors = ['red', 'blue', 'green', 'orange', 'brown', 'purple']

        self.lines = []
        for i, (ax, title, color) in enumerate(zip(self.axes.flat, titles, colors)):
            ax.set_title(title)
            ax.set_xlabel('Время (с)')
            ax.grid(True, alpha=0.3)
            line, = ax.plot([], [], color=color, linewidth=1.5)
            self.lines.append(line)

        self.canvas = FigureCanvasTkAgg(self.fig, center_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(expand=True, fill='both')

        # Правая панель - управление
        right_frame = ttk.LabelFrame(main_frame, text="Управление", padding="10")
        right_frame.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)

        # Ручное управление
        ttk.Label(right_frame, text="РУЧНОЕ УПРАВЛЕНИЕ", font=('Arial', 12, 'bold')).pack(pady=5)

        self.manual_var = tk.BooleanVar()
        ttk.Checkbutton(right_frame, text="Ручной режим",
                        variable=self.manual_var,
                        command=self.toggle_manual_mode).pack(pady=5)

        # Слайдеры для ручного управления
        ttk.Label(right_frame, text="Вентилятор (%):").pack()
        self.fan_slider = ttk.Scale(right_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=200)
        self.fan_slider.set(50)
        self.fan_slider.pack(pady=2)

        ttk.Label(right_frame, text="Нагреватель (%):").pack()
        self.heater_slider = ttk.Scale(right_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=200)
        self.heater_slider.set(0)
        self.heater_slider.pack(pady=2)

        ttk.Label(right_frame, text="Охладитель (%):").pack()
        self.cooler_slider = ttk.Scale(right_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=200)
        self.cooler_slider.set(0)
        self.cooler_slider.pack(pady=2)

        ttk.Label(right_frame, text="Увлажнитель (%):").pack()
        self.humidifier_slider = ttk.Scale(right_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=200)
        self.humidifier_slider.set(0)
        self.humidifier_slider.pack(pady=2)

        # Управление симуляцией
        ttk.Label(right_frame, text="\nУПРАВЛЕНИЕ СИМУЛЯЦИЕЙ",
                  font=('Arial', 12, 'bold')).pack(pady=5)

        ttk.Label(right_frame, text="Скорость симуляции:").pack()
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_combo = ttk.Combobox(right_frame, textvariable=self.speed_var,
                                   values=[0.5, 1.0, 2.0, 5.0, 10.0], width=10)
        speed_combo.pack(pady=2)

        # Кнопки управления
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(pady=10)

        self.start_button = ttk.Button(button_frame, text="▶ Старт",
                                       command=self.start_simulation, width=10)
        self.start_button.grid(row=0, column=0, padx=2)

        self.stop_button = ttk.Button(button_frame, text="⏹ Стоп",
                                      command=self.stop_simulation, width=10)
        self.stop_button.grid(row=0, column=1, padx=2)

        self.reset_button = ttk.Button(button_frame, text="↺ Сброс",
                                       command=self.reset_simulation, width=10)
        self.reset_button.grid(row=1, column=0, padx=2, pady=5)

        self.analyze_button = ttk.Button(right_frame, text="📊 Анализ правил",
                                         command=self.show_rules_analysis, width=20)
        self.analyze_button.pack(pady=5)

        # Информационная панель
        info_frame = ttk.LabelFrame(right_frame, text="Информация", padding="5")
        info_frame.pack(fill='both', expand=True, pady=10)

        self.info_text = tk.Text(info_frame, height=8, width=30, wrap=tk.WORD)
        self.info_text.pack(expand=True, fill='both')

        scrollbar = ttk.Scrollbar(info_frame, command=self.info_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.info_text.config(yscrollcommand=scrollbar.set)

        # Настройка весов для grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Запуск обновления в ручном режиме
        self.update_manual()

    def toggle_manual_mode(self):
        """Переключение режима управления"""
        self.manual_mode = self.manual_var.get()

        if self.manual_mode:
            # Включаем слайдеры
            for slider in [self.fan_slider, self.heater_slider,
                           self.cooler_slider, self.humidifier_slider]:
                slider.state(['!disabled'])
        else:
            # Выключаем слайдеры
            for slider in [self.fan_slider, self.heater_slider,
                           self.cooler_slider, self.humidifier_slider]:
                slider.state(['disabled'])

    def update_manual(self):
        """Обновление при ручном управлении"""
        if self.manual_mode and not self.is_running:
            self.fan_speed = self.fan_slider.get()
            self.heater_power = self.heater_slider.get()
            self.cooler_power = self.cooler_slider.get()
            self.humidifier_power = self.humidifier_slider.get()
            self.update_display()

        self.root.after(100, self.update_manual)

    def start_simulation(self):
        """Запуск симуляции"""
        if not self.is_running:
            self.is_running = True
            self.simulation_thread = threading.Thread(target=self.simulation_loop)
            self.simulation_thread.daemon = True
            self.simulation_thread.start()
            self.add_info("Симуляция запущена")

    def stop_simulation(self):
        """Остановка симуляции"""
        self.is_running = False
        self.add_info("Симуляция остановлена")

    def reset_simulation(self):
        """Сброс всех параметров"""
        self.is_running = False

        # Сброс переменных
        self.current_temp = 22.0
        self.current_humidity = 50.0
        self.current_co2 = 400.0
        self.fan_speed = 50.0
        self.heater_power = 0.0
        self.cooler_power = 0.0
        self.humidifier_power = 0.0

        # Сброс симулятора
        self.simulator = WorkshopSimulator()

        # Сброс истории
        self.time_history = []
        self.temp_history = []
        self.humidity_history = []
        self.co2_history = []
        self.fan_history = []
        self.heater_history = []
        self.cooler_history = []
        self.humidifier_history = []

        self.update_display()
        self.update_graphs()
        self.add_info("Симуляция сброшена")

    def simulation_loop(self):
        """Основной цикл симуляции"""
        dt_model = 1.0  # Базовый шаг модельного времени (1 секунда)
        step = 0
        last_real_time = time.time()

        while self.is_running:
            loop_start = time.time()

            # Получаем текущую скорость из виджета
            self.simulation_speed = self.speed_var.get()

            # Обновление внешней среды с учетом ускорения
            self.simulator.update_environment(dt_model * self.simulation_speed)

            if not self.manual_mode:
                # Автоматический режим - используем нечеткий контроллер
                control_outputs = self.fuzzy_controller.compute(
                    self.current_temp, self.current_humidity, self.current_co2
                )

                self.fan_speed = control_outputs['fan_speed']
                self.heater_power = control_outputs['heater_power']
                self.cooler_power = control_outputs['cooler_power']
                self.humidifier_power = control_outputs['humidifier_power']

            # Расчет изменений параметров с учетом ускорения
            # dt_model * self.simulation_speed - сколько модельных секунд прошло за этот шаг
            d_temp, d_humidity, d_co2 = self.simulator.calculate_changes(
                self.current_temp, self.current_humidity, self.current_co2,
                self.fan_speed, self.heater_power, self.cooler_power, self.humidifier_power,
                dt_model * self.simulation_speed  # ← КЛЮЧЕВОЕ ИЗМЕНЕНИЕ
            )

            # Обновление параметров
            self.current_temp += d_temp
            self.current_humidity += d_humidity
            self.current_co2 += d_co2

            # Ограничения
            self.current_temp = max(0, min(50, self.current_temp))
            self.current_humidity = max(0, min(100, self.current_humidity))
            self.current_co2 = max(0, min(2000, self.current_co2))

            # Сохранение истории (каждый шаг - одна модельная секунда)
            current_time = step * dt_model
            self.time_history.append(current_time)
            self.temp_history.append(self.current_temp)
            self.humidity_history.append(self.current_humidity)
            self.co2_history.append(self.current_co2)
            self.fan_history.append(self.fan_speed)
            self.heater_history.append(self.heater_power)
            self.cooler_history.append(self.cooler_power)
            self.humidifier_history.append(self.humidifier_power)

            # Ограничение длины истории
            if len(self.time_history) > self.max_history:
                for hist in [self.time_history, self.temp_history, self.humidity_history,
                             self.co2_history, self.fan_history, self.heater_history,
                             self.cooler_history, self.humidifier_history]:
                    hist.pop(0)

            # Обновление онтологии
            self.ontology.update_sensors(
                self.current_temp, self.current_humidity, self.current_co2
            )
            self.ontology.update_actuators(
                self.fan_speed, self.heater_power, self.cooler_power, self.humidifier_power
            )

            # Обновление отображения
            self.root.after(0, self.update_display)
            if step % 5 == 0:
                self.root.after(0, self.update_graphs)

            step += 1

            # Управление скоростью цикла - фиксированная пауза
            # Чем выше simulation_speed, тем быстрее итерации
            elapsed = time.time() - loop_start
            # Базовая задержка 0.05 сек, но при высокой скорости делаем её меньше
            base_delay = 0.05
            # При speed=10 задержка 0.005 сек, что дает ~200 итераций/сек
            delay = base_delay / self.simulation_speed
            sleep_time = max(0, delay - elapsed)
            time.sleep(sleep_time)

    def update_display(self):
        """Обновление цифровых индикаторов"""
        # Датчики
        self.temp_label.config(text=f"{self.current_temp:.1f}°C")
        self.temp_progress['value'] = self.current_temp

        self.humidity_label.config(text=f"{self.current_humidity:.1f}%")
        self.humidity_progress['value'] = self.current_humidity

        self.co2_label.config(text=f"{self.current_co2:.0f} ppm")
        self.co2_progress['value'] = self.current_co2

        # Исполнительные устройства
        self.fan_label.config(text=f"{self.fan_speed:.0f}%")
        self.fan_progress['value'] = self.fan_speed

        self.heater_label.config(text=f"{self.heater_power:.0f}%")
        self.heater_progress['value'] = self.heater_power

        self.cooler_label.config(text=f"{self.cooler_power:.0f}%")
        self.cooler_progress['value'] = self.cooler_power

        self.humidifier_label.config(text=f"{self.humidifier_power:.0f}%")
        self.humidifier_progress['value'] = self.humidifier_power

        # Внешние условия
        self.ext_temp_label.config(text=f"{self.simulator.external_temp:.1f}°C")
        self.ext_humidity_label.config(text=f"{self.simulator.external_humidity:.1f}%")

        hours = int(self.simulator.time_of_day)
        minutes = int((self.simulator.time_of_day - hours) * 60)
        self.time_label.config(text=f"{hours:02d}:{minutes:02d}")

    def update_graphs(self):
        """Обновление графиков"""
        if not self.time_history:
            return

        data_series = [
            (self.time_history, self.temp_history),
            (self.time_history, self.humidity_history),
            (self.time_history, self.co2_history),
            (self.time_history, self.fan_history),
            (self.time_history, self.heater_history),
            (self.time_history, self.cooler_history)
        ]

        for i, (line, (x_data, y_data)) in enumerate(zip(self.lines, data_series)):
            line.set_data(x_data, y_data)
            ax = self.axes.flat[i]
            ax.relim()
            ax.autoscale_view()

        self.fig.tight_layout(pad=3.0)
        self.canvas.draw()

    def add_info(self, message):
        """Добавление сообщения в информационное окно"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.info_text.insert('1.0', f"[{timestamp}] {message}\n")
        if float(self.info_text.index('end-1c').split('.')[0]) > 100:
            self.info_text.delete('50.0', 'end')

    def show_rules_analysis(self):
        """Показ анализа правил нечеткой логики"""
        window = tk.Toplevel(self.root)
        window.title("Анализ правил управления")
        window.geometry("600x500")

        text = tk.Text(window, wrap=tk.WORD, font=('Courier', 10))
        text.pack(expand=True, fill='both', padx=10, pady=10)

        rules_text = """
        АНАЛИЗ ПРАВИЛ НЕЧЕТКОЙ ЛОГИКИ
        ================================

        ВХОДНЫЕ ПЕРЕМЕННЫЕ:
        -------------------
        1. Температура (0-50°C):
           - Очень холодно: 0-10°C
           - Холодно: 5-18°C
           - Нормально: 16-26°C
           - Тепло: 23-33°C
           - Жарко: 30-50°C

        2. Влажность (0-100%):
           - Очень сухо: 0-20%
           - Сухо: 15-45%
           - Оптимально: 40-60%
           - Влажно: 55-85%
           - Очень влажно: 80-100%

        3. CO₂ (0-2000 ppm):
           - Низкий: 0-400 ppm
           - Нормальный: 300-800 ppm
           - Повышенный: 600-1500 ppm
           - Высокий: 1200-2000 ppm

        ПРАВИЛА УПРАВЛЕНИЯ:
        ------------------
        Температура:
        - Очень холодно → Нагреватель: высоко, Вентилятор: низко
        - Холодно → Нагреватель: низко, Вентилятор: низко
        - Нормально → Все выкл, Вентилятор: средне
        - Тепло → Охладитель: низко, Вентилятор: средне
        - Жарко → Охладитель: высоко, Вентилятор: высоко

        Влажность:
        - Очень сухо → Увлажнитель: высоко, Вентилятор: низко
        - Сухо → Увлажнитель: низко, Вентилятор: низко
        - Оптимально → Увлажнитель: выкл, Вентилятор: средне
        - Влажно → Вентилятор: высоко
        - Очень влажно → Вентилятор: максимум

        CO₂:
        - Повышенный → Вентилятор: высоко
        - Высокий → Вентилятор: максимум
        - Низкий + Норм. темп → Вентилятор: низко

        ВЫХОДНЫЕ ПЕРЕМЕННЫЕ:
        --------------------
        - Скорость вентилятора (0-100%)
        - Мощность нагревателя (0-100%)
        - Мощность охладителя (0-100%)
        - Мощность увлажнителя (0-100%)

        ПРИОРИТЕТЫ ПРАВИЛ:
        ------------------
        1. Безопасность (CO₂ > 1500 ppm → макс. вентиляция)
        2. Комфорт (температура 20-24°C, влажность 40-60%)
        3. Энергоэффективность (минимальное использование ресурсов)
        """

        text.insert('1.0', rules_text)
        text.config(state='disabled')

    def run(self):
        """Запуск GUI"""
        self.root.mainloop()


def main():
    """Точка входа в приложение"""
    app = VentilationGUI()
    app.run()


if __name__ == '__main__':
    main()