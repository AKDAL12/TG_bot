import telebot
import psycopg2
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time

# Токен Telegram-бота
TOKEN = '7825077866:AAFnTGqpayF81VaFU-NRRYk3rgjxji4srO4'
bot = telebot.TeleBot(TOKEN)

# Подключение к базе данных PostgreSQL
conn = psycopg2.connect(
    dbname="postgres",
    user="alex",
    password="1234",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# Глобальный словарь для хранения счетов пользователей
user_scores = {}

# Словарь для хранения контекста пользователей
user_context = {}

# Функция для получения user_id по chat_id
def get_user_id_by_chat_id(chat_id):
    try:
        cursor.execute("SELECT id FROM users WHERE chat_id = %s;", (chat_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        print(f"Ошибка получения ID пользователя: {e}")
        return None

# Функция для регистрации пользователя
def register_user(chat_id, username, full_name, age):
    try:
        cursor.execute("SELECT id FROM users WHERE chat_id = %s;", (chat_id,))
        user = cursor.fetchone()
        if user:
            print(f"Пользователь с chat_id={chat_id} уже зарегистрирован с id={user[0]}.")
            return user[0]
        
        cursor.execute(
            """
            INSERT INTO users (chat_id, username, full_name, age, registration_date)
            VALUES (%s, %s, %s, %s, NOW())
            RETURNING id;
            """,
            (chat_id, username, full_name, age)
        )
        user_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Пользователь успешно зарегистрирован: chat_id={chat_id}, id={user_id}.")
        return user_id
    except Exception as e:
        conn.rollback()
        print(f"Ошибка регистрации пользователя: {e}")
        return None

def get_user_id_by_chat_id(chat_id):
    try:
        cursor.execute("SELECT id FROM users WHERE chat_id = %s;", (chat_id,))
        result = cursor.fetchone()
        print(f"Получен user_id для chat_id={chat_id}: {result}")
        return result[0] if result else None
    except psycopg2.Error as e:
        print(f"Ошибка получения user_id: {e}")
        return None

# Функция для добавления прогресса пользователя
def add_user_progress(user_id, topic_id, sub_id, is_correct):
    try:
        # Пропускаем запись, если ответ неверный
        if not is_correct:
            print(f"Ответ на задание sub_id={sub_id} от пользователя user_id={user_id} неверный. Прогресс не обновляется.")
            return

        # Проверяем, есть ли уже запись о правильном ответе для данного sub_id
        cursor.execute(
            "SELECT 1 FROM user_progress WHERE user_id = %s AND sub_id = %s AND is_correct = TRUE;",
            (user_id, sub_id)
        )
        if cursor.fetchone():
            print(f"Запись о правильном ответе на sub_id={sub_id} от user_id={user_id} уже существует. Пропускаем.")
            return

        # Если записи нет, добавляем новую
        cursor.execute(
            """
            INSERT INTO user_progress (user_id, topic_id, sub_id, is_correct, completion_date)
            VALUES (%s, %s, %s, %s, NOW());
            """,
            (user_id, topic_id, sub_id, is_correct)
        )
        conn.commit()
        print(f"Прогресс пользователя {user_id} по вопросу {sub_id} успешно обновлен.")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Ошибка добавления прогресса пользователя: {e}")

# Функция для увеличения счета пользователя в таблице лидеров
def increment_user_score(user_id):
    try:
        cursor.execute(
            """
            INSERT INTO leaderboard (user_id, correct_answers)
            VALUES (%s, 1)
            ON CONFLICT (user_id)
            DO UPDATE SET correct_answers = leaderboard.correct_answers + 1;
            """,
            (user_id,)
        )
        conn.commit()
        print(f"Счёт пользователя {user_id} увеличен.")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Ошибка обновления счёта пользователя: {e}")
        # Увеличиваем количество правильных ответов в таблице лидеров
        cursor.execute(
            """
            INSERT INTO leaderboard (user_id, correct_answers)
            VALUES (%s, 1)
            ON CONFLICT (user_id)
            DO UPDATE SET correct_answers = leaderboard.correct_answers + 1;
            """,
            (user_id,)
        )
        conn.commit()
        print(f"Таблица лидеров обновлена для пользователя {user_id}.")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Ошибка обновления таблицы лидеров: {e}")

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = get_user_id_by_chat_id(message.chat.id)

    if user_id:
        # Пользователь уже зарегистрирован, показываем главное меню
        show_main_menu(message.chat.id)
    else:
        # Пользователь не зарегистрирован, предлагаем зарегистрироваться
        markup = InlineKeyboardMarkup()
        register_button = InlineKeyboardButton("Регистрация", callback_data="register")
        markup.add(register_button)

        bot.send_message(
            message.chat.id,
            "Привет! Я бот для помощи в изучени SQL. Прежде чем начать, пожалуйста, зарегистрируйтесь, нажав кнопку ниже.",
            reply_markup=markup
        )

# Функция для отображения главного меню
def show_main_menu(chat_id):
    try:
        markup = InlineKeyboardMarkup()
        topics_button = InlineKeyboardButton("Список тем", callback_data="show_topics")
        leaderboard_button = InlineKeyboardButton("Таблица лидеров", callback_data="leaderboard")
        personal_score_button = InlineKeyboardButton("Личный счет", callback_data="personal_score")

        markup.add(topics_button, leaderboard_button, personal_score_button)
        bot.send_message(
            chat_id,
            "Выберите действие, нажав на одну из кнопок ниже. Если появятся вопросы то просто напиши /help",
            reply_markup=markup
        )
        print(f"Главное меню отправлено пользователю chat_id={chat_id}.")
    except Exception as e:
        print(f"Ошибка при отправке главного меню: {e}")

# Обработчик для кнопки "Личный счет"
@bot.callback_query_handler(func=lambda call: call.data == "personal_score")
def handle_personal_score(call):
    chat_id = call.message.chat.id
    user_id = get_user_id_by_chat_id(chat_id)

    if not user_id:
        bot.send_message(chat_id, "Вы не зарегистрированы. Используйте команду /start для регистрации.")
        return

    # Получаем имя пользователя из таблицы users
    cursor.execute(
        "SELECT full_name FROM users WHERE id = %s;",
        (user_id,)
    )
    result = cursor.fetchone()
    full_name = result[0] if result else "Неизвестный пользователь"

    # Получаем данные из таблицы leaderboard
    cursor.execute(
        """
        SELECT user_id, correct_answers
        FROM leaderboard
        ORDER BY correct_answers DESC;
        """
    )
    leaderboard = cursor.fetchall()

    # Определяем место пользователя и его количество правильных ответов
    user_place = None
    correct_answers = 0
    for i, (leader_id, score) in enumerate(leaderboard, start=1):
        if leader_id == user_id:
            user_place = i
            correct_answers = score
            break

    # Формируем сообщение
    if user_place is not None:
        message = (f"ℹ️ Имя пользователя: {full_name}\n"
                   f"🎯 Ваш личный счет: {correct_answers} правильных ответов.\n"
                   f"🏆 Место в таблице лидеров: {user_place}.")
    else:
        message = (f"ℹ️ Имя пользователя: {full_name}\n"
                   f"🎯 Ваш личный счет: 0 правильных ответов.\n"
                   f"Вы еще не попали в таблицу лидеров.")

    # Создаем кнопку для сброса счета
    markup = InlineKeyboardMarkup()
    reset_button = InlineKeyboardButton("Сбросить счет", callback_data="reset_score")
    markup.add(reset_button)

    bot.send_message(chat_id, message, reply_markup=markup)
# Обработчик кнопки "Сбросить счет"
@bot.callback_query_handler(func=lambda call: call.data == "reset_score")
def handle_reset_score(call):
    chat_id = call.message.chat.id
    user_id = get_user_id_by_chat_id(chat_id)

    if not user_id:
        bot.send_message(chat_id, "Вы не зарегистрированы. Используйте команду /start для регистрации.")
        return

    try:
        # Начинаем транзакцию
        cursor.execute("BEGIN;")

        # Удаляем данные пользователя из таблицы user_progress
        cursor.execute(
            "DELETE FROM user_progress WHERE user_id = %s;",
            (user_id,)
        )

        # Удаляем данные пользователя из таблицы лидеров
        cursor.execute(
            "DELETE FROM leaderboard WHERE user_id = %s;",
            (user_id,)
        )

        bot.send_message(chat_id, "Ваш счет и данные из таблицы лидеров успешно сброшены. Начните заново и улучшите результат!")

    except Exception as e:
        # Откатываем изменения в случае ошибки
        print(f"Ошибка при сбросе счета: {e}")
        bot.send_message(chat_id, "Произошла ошибка при сбросе счета. Пожалуйста, попробуйте позже.")

# Обработчик для кнопки "Регистрация"
@bot.callback_query_handler(func=lambda call: call.data == "register")
def handle_register_button(call):
    bot.send_message(call.message.chat.id, "Введите ваше полное имя:")
    bot.register_next_step_handler(call.message, get_full_name)

def get_full_name(message):
    full_name = message.text.strip()
    bot.send_message(message.chat.id, "Введите ваш возраст:")
    bot.register_next_step_handler(message, get_age, full_name)

def get_age(message, full_name):
    try:
        age = int(message.text.strip())
        user_id = register_user(message.chat.id, message.from_user.username, full_name, age)
        if user_id:
            bot.send_message(message.chat.id, "Регистрация успешна!")
            show_main_menu(message.chat.id)  # Показ главного меню после успешной регистрации
        else:
            bot.send_message(message.chat.id, "Ошибка при регистрации. Попробуйте снова.")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный возраст.")
    except Exception as e:
        print(f"Ошибка в процессе регистрации: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при регистрации.")

# Обработчик для кнопки "Таблица лидеров"
@bot.callback_query_handler(func=lambda call: call.data == "leaderboard")
def handle_leaderboard_button(call):
    show_leaderboard(call.message)

# Обработчик для кнопки "Показать список тем"
@bot.callback_query_handler(func=lambda call: call.data == "show_topics")
def handle_show_topics(call):
    show_topics(call.message)

# Команда /topics
@bot.message_handler(commands=['topics'])
def show_topics(message):
    try:
        cursor.execute("SELECT id, name FROM topics ORDER BY id;")  # Сортировка по ID
        topics = cursor.fetchall()

        response = "Доступные темы:\n"
        markup = InlineKeyboardMarkup()

        for topic in topics:
            response += f"{topic[0]}. {topic[1]}\n"
            button = InlineKeyboardButton(text=topic[1], callback_data=f"topic:{topic[0]}")
            markup.add(button)

        response += "\nВыберите тему через команду или нажмите на кнопку."
        bot.send_message(message.chat.id, response, reply_markup=markup)
    except psycopg2.Error as e:
        print(f"Ошибка при получении тем: {e}")
        bot.send_message(message.chat.id, "Ошибка при получении тем.")

# Обработчик кнопок для выбора темы
@bot.callback_query_handler(func=lambda call: call.data.startswith("topic:"))
def handle_topic_button(call):
    try:
        topic_id = int(call.data.split(":")[1])  # Извлекаем ID темы
        cursor.execute("SELECT name, description FROM topics WHERE id = %s;", (topic_id,))
        topic = cursor.fetchone()
        if topic:
            response = f"Тема: {topic[0]}\nОписание: {topic[1]}"
            markup = InlineKeyboardMarkup()
            start_button = InlineKeyboardButton("Начать тест", callback_data=f"start_test:{topic_id}")
            markup.add(start_button)
            bot.send_message(call.message.chat.id, response, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, "Тема не найдена. Проверьте правильность выбора.")
    except psycopg2.Error as e:
        print(f"Ошибка при обработке темы: {e}")
        bot.send_message(call.message.chat.id, "Ошибка при обработке темы.")
        # Обработчик кнопки "Начать тест"
@bot.callback_query_handler(func=lambda call: call.data.startswith("start_test:"))
def handle_start_test_button(call):
    try:
        topic_id = int(call.data.split(":")[1])  # Извлекаем ID темы
        show_task(call.message, topic_id)
    except ValueError:
        bot.send_message(call.message.chat.id, "Некорректный ID темы.")

# Команда /task <номер_темы>
def show_task(message, topic_id):
    try:
        sub_id = topic_id
        user_context[message.chat.id] = {'topic_id': topic_id, 'sub_id': sub_id}
        
        # Получаем первое задание
        cursor.execute("SELECT question, example FROM tasks WHERE sub_id = %s;", (sub_id,))
        task = cursor.fetchone()
        if task:  # Проверяем, что задание найдено
            response = f"Задание:\n{task[0]}\nПример:\n{task[1]}\nНапишите свой ответ ниже."
            bot.send_message(message.chat.id, response)
            bot.register_next_step_handler(message, check_answer)
        else:
            bot.send_message(message.chat.id, "Задание не найдено.")
    except psycopg2.Error as e:
        print(f"Ошибка при показе задания: {e}")
        bot.send_message(message.chat.id, "Ошибка при показе задания.")
    except Exception as e:
        print(f"Общая ошибка в show_task: {e}")
        bot.send_message(message.chat.id, f"Ошибка: {e}")

# Функция для проверки ответа пользователя
def check_answer(message):
    try:
        chat_id = message.chat.id
        sub_id = user_context[chat_id]['sub_id']
        user_answer = message.text.strip()

        # Получаем правильный ответ из базы данных
        cursor.execute("SELECT answer FROM tasks WHERE sub_id = %s;", (sub_id,))
        result = cursor.fetchone()
        if not result:
            bot.send_message(chat_id, "Неверный идентификатор задания.")
            return
        correct_answer = result[0]

        # Получаем или регистрируем пользователя
        user_id = get_user_id_by_chat_id(chat_id)
        if not user_id:
            user_id = register_user(chat_id, "unknown", "Unknown User", 0)
            if not user_id:
                print(f"Не удалось зарегистрировать пользователя с chat_id={chat_id}.")
                return

        # Проверка правильности ответа
        if user_answer.lower() == correct_answer.lower():
            # Проверяем, существует ли запись в таблице прогресса
            cursor.execute(
                "SELECT 1 FROM user_progress WHERE user_id = %s AND sub_id = %s;",
                (user_id, sub_id)
            )
            progress_exists = cursor.fetchone()

            if not progress_exists:
                # Добавляем в прогресс
                add_user_progress(user_id, user_context[chat_id]['topic_id'], sub_id, True)

                # Увеличиваем счёт в таблице лидеров
                increment_user_score(user_id)

                # Обновляем локальный счётчик
                user_scores[chat_id] = user_scores.get(chat_id, 0) + 1

                bot.send_message(chat_id, "Верно! Отличная работа!")
            else:
                bot.send_message(chat_id, "Вы уже отвечали на этот вопрос правильно.")
                user_scores[chat_id] = user_scores.get(chat_id, 0) + 1
        else:
            bot.send_message(chat_id, f"Неправильно. Правильный ответ:\n{correct_answer}")
            
            # Переход к следующему вопросу
        go_to_next_task(message)
    except KeyError:
        bot.send_message(message.chat.id, "Ошибка: Контекст пользователя не найден.")
    except psycopg2.Error as e:
        print(f"Ошибка при проверке ответа: {e}")
        bot.send_message(message.chat.id, "Ошибка при проверке ответа.")
    except Exception as e:
        print(f"Общая ошибка в check_answer: {e}")
        bot.send_message(message.chat.id, f"Ошибка: {e}")

# Функция для перехода к следующему вопросу
def go_to_next_task(message):
    try:
        topic_id = user_context[message.chat.id]['topic_id']
        sub_id = user_context[message.chat.id]['sub_id']
        next_sub_id = sub_id + 100  # Логика получения следующего задания
        cursor.execute("SELECT question, example FROM tasks WHERE sub_id = %s;", (next_sub_id,))
        next_task = cursor.fetchone()

        if next_task:
            # Переход к следующему вопросу
            response = f"Следующий вопрос:\n{next_task[0]}\nПример:\n{next_task[1]}\nНапишите свой ответ ниже."
            bot.send_message(message.chat.id, response)
            user_context[message.chat.id]['sub_id'] = next_sub_id
            bot.register_next_step_handler(message, check_answer)
        else:
            # Если вопросов больше нет, показываем результат и кнопки
            user_score = user_scores.get(message.chat.id, 0)

            markup = InlineKeyboardMarkup()
            main_menu_button = InlineKeyboardButton("Главное меню", callback_data="go_to_main_menu")
            next_topic_button = InlineKeyboardButton("Перейти к темам", callback_data=f"show_topics")
            markup.add(main_menu_button, next_topic_button)

            bot.send_message(
                message.chat.id,
                f"Вы завершили тему! Ваш результат: {user_score} правильных ответов.\nЧто вы хотите делать дальше?",
                reply_markup=markup
            )
            reset_user_score(message.chat.id)  # Сбрасываем счетчик правильных ответов
    except KeyError:
        bot.send_message(message.chat.id, "Ошибка: Контекст пользователя не найден.")
    except psycopg2.Error as e:
        print(f"Ошибка при переходе к следующему заданию: {e}")
        bot.send_message(message.chat.id, "Ошибка при переходе к следующему заданию.")
    except Exception as e:
        print(f"Общая ошибка в go_to_next_task: {e}")
        bot.send_message(message.chat.id, f"Ошибка: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("next_topic:"))
def handle_next_topic(call):
    try:
        next_topic_id = int(call.data.split(":")[1])
        cursor.execute("SELECT id FROM topics WHERE id = %s;", (next_topic_id,))
        next_topic = cursor.fetchone()

        if next_topic:
            # Открываем следующую тему
            show_task(call.message, next_topic_id)
        else:
            bot.send_message(call.message.chat.id, "Следующая тема не найдена.")
    except ValueError:
        bot.send_message(call.message.chat.id, "Ошибка: Некорректный идентификатор темы.")
    except Exception as e:
        print(f"Ошибка в handle_next_topic: {e}")
        bot.send_message(call.message.chat.id, "Ошибка при переходе к следующей теме.")

# Функция для отображения таблицы лидеров
def show_leaderboard(message):
    try:
        cursor.execute("""
            SELECT u.full_name, l.correct_answers
            FROM leaderboard l
            JOIN users u ON l.user_id = u.id
            ORDER BY l.correct_answers DESC, u.full_name ASC
            LIMIT 10;
        """)
        leaderboard = cursor.fetchall()
        if leaderboard:
            response = "🏆 Таблица лидеров:\n\n"
            for index, (full_name, correct_answers) in enumerate(leaderboard, start=1):
                response += f"{index}. {full_name} — {correct_answers} правильных ответов\n"
        else:
            response = "Таблица лидеров пока пуста."
        bot.send_message(message.chat.id, response)
    except Exception as e:
        print(f"Ошибка при выводе таблицы лидеров: {e}")
        bot.send_message(message.chat.id, f"Ошибка при выводе таблицы лидеров: {e}")

# Команда /help
@bot.message_handler(commands=['help'])
def show_help(message):
    help_text = (
        "Привет! Я помогу тебе изучить базы данных. Вот что я могу делать:\n\n"

        "1. /start - Сообщения для вывода главного меню. \n"
        "2. /topics - Показать список всех доступных тем.\n"
    )
    bot.send_message(message.chat.id, help_text)

# Регистрация пользователя через команду /register
@bot.message_handler(commands=['register'])
def handle_register(message):
    try:
        bot.send_message(message.chat.id, "Введите ваше полное имя:")
        bot.register_next_step_handler(message, get_full_name)
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

def get_full_name(message):
    full_name = message.text.strip()
    bot.send_message(message.chat.id, "Введите ваш возраст:")
    bot.register_next_step_handler(message, get_age, full_name)

def get_age(message, full_name):
    try:
        age = int(message.text.strip())
        user_id = register_user(message.chat.id, message.from_user.username, full_name, age)
        if user_id:
            markup = InlineKeyboardMarkup()
            start_button = InlineKeyboardButton("Перейти в главное меню", callback_data="go_to_main_menu")
            markup.add(start_button)

            bot.send_message(
                message.chat.id,
                "Регистрация успешна! Нажмите кнопку ниже, чтобы перейти в главное меню.",
                reply_markup=markup
            )
        else:
            bot.send_message(message.chat.id, "Ошибка при регистрации. Попробуйте снова.")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный возраст.")
    except Exception as e:
        print(f"Ошибка в процессе регистрации: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при регистрации.")

@bot.callback_query_handler(func=lambda call: call.data == "go_to_main_menu")
def handle_go_to_main_menu(call):
    send_welcome(call.message)  # Вызываем функцию для отображения главного меню

def reset_user_score(user_id):
    user_scores[user_id] = 0

# Запуск бота
if __name__ == "__main__":
    try:
        print("Бот запущен...")
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
        time.sleep(5)
