from sklearn.linear_model import LinearRegression
import numpy as np

def predict_card_completion_time(user_id, actual_time_new, status_card_id_new, user_cards_data):

    # Получаем данные о карточках данного пользователя
    user_data = user_cards_data.get(user_id)

    # Проверяем, есть ли у пользователя данные о карточках
    if user_data is None or len(user_data) == 0:
        raise ValueError("No card data available for the specified user")

    # Формируем данные для обучения модели
    X = []  # Признаки
    y = []  # Целевая переменная (время выполнения)

    for card_data in user_data:
        # Преобразуем время в секунды
        actual_seconds = card_data['actual_time'].hour * 3600 + card_data['actual_time'].minute * 60 + card_data['actual_time'].second
        X.append([actual_seconds, card_data['status_card_id']])  # Признаки: затраченное время, статус карточки
        # Преобразуем время в секунды
        estimated_seconds = card_data['estimated_time'].hour * 3600 + card_data['estimated_time'].minute * 60 + card_data['estimated_time'].second
        y.append(estimated_seconds)  # Целевая переменная: предполагаемое время выполнения

    # Преобразуем в массивы numpy и в 2D формат
    X = np.array(X).reshape(-1, 2)
    y = np.array(y)

    # Создаем и обучаем модель линейной регрессии
    model = LinearRegression()
    model.fit(X, y)

    # Делаем предсказание для новой карточки
    actual_seconds_new = actual_time_new // 3600 * 3600  # Округляем до часов
    estimated_time_new = model.predict([[actual_seconds_new, status_card_id_new]])[0]

    return estimated_time_new
