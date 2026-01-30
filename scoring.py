import sqlite3

DB_PATH = "gifts.db"

# Порядок бюджетов
BUDGET_ORDER = ["budget_2000", "budget_5000", "budget_10000", "budget_15000",
                "budget_20000", "budget_30000", "budget_50000", "budget_100000"]


def calculate_budget_score(user_max_budget: str, gift_budget_tags: str) -> float:
    """
    Рассчитывает баллы за соответствие бюджета.
    
    Логика:
    - Если бюджет юзера попадает в нижнюю границу диапазона товара → штраф
    - Если в середину → нейтрально
    - Если в верхнюю границу → бонус
    """
    if not user_max_budget or not gift_budget_tags:
        return 0.0
    
    # Индекс бюджета пользователя
    if user_max_budget not in BUDGET_ORDER:
        return 0.0
    user_index = BUDGET_ORDER.index(user_max_budget)
    
    # Находим диапазон бюджета товара
    gift_indices = []
    for i, tag in enumerate(BUDGET_ORDER):
        if tag in gift_budget_tags:
            gift_indices.append(i)
    
    if not gift_indices:
        return 0.0
    
    gift_min_index = min(gift_indices)
    gift_max_index = max(gift_indices)
    
    # Если бюджет юзера ниже минимума товара — товар не подходит (отсеется фильтром)
    if user_index < gift_min_index:
        return -10.0
    
    # Если бюджет юзера выше максимума товара — товар дешевле чем юзер готов потратить
    if user_index > gift_max_index:
        # Чем больше разница, тем меньше баллов (слишком дёшево для бюджета)
        diff = user_index - gift_max_index
        if diff == 1:
            return 0.5  # Немного дешевле — ок
        elif diff == 2:
            return 0.0  # Заметно дешевле — нейтрально
        else:
            return -0.5 * (diff - 2)  # Сильно дешевле — штраф
    
    # Бюджет юзера внутри диапазона товара
    if gift_max_index == gift_min_index:
        # Товар с одним бюджетом — точное попадание
        return 2.0
    
    # Рассчитываем позицию в диапазоне (0 = нижняя граница, 1 = верхняя)
    position = (user_index - gift_min_index) / (gift_max_index - gift_min_index)
    
    # Преобразуем позицию в баллы
    # position = 0 → -1.0 балл (нижняя граница, товар скорее дороже)
    # position = 0.5 → +0.5 балл (середина)
    # position = 1 → +2.0 балла (верхняя граница, идеальное попадание)
    
    if position <= 0.25:
        return -1.0  # Нижняя граница — штраф
    elif position <= 0.5:
        return 0.0   # Ниже середины — нейтрально
    elif position <= 0.75:
        return 1.0   # Выше середины — хорошо
    else:
        return 2.0   # Верхняя граница — отлично


def filter_and_score_gifts(filters: dict, value_weights: dict, interest_weights: dict):
    """
    Фильтрует подарки по PRIMARY тегам и считает score по VALUE/INTERESTS
    """
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gifts")
    all_gifts = cursor.fetchall()
    conn.close()
    
    results = []
    
    for gift in all_gifts:
        gift_id = gift[0]
        name = gift[1]
        price = gift[2]
        description = gift[3]
        budget_tags = str(gift[4] or '')
        gender_tags = str(gift[5] or '')
        age_tags = str(gift[6] or '')
        relationship_tags = str(gift[7] or '')
        occasion_tags = str(gift[8] or '')
        value_tags = str(gift[9] or '')
        interest_tags = str(gift[10] or '')
        
        # === PRIMARY ФИЛЬТРАЦИЯ ===
        
        # Бюджет (хотя бы один тег должен совпасть)
        if 'budget' in filters:
            budget_match = any(b in budget_tags for b in filters['budget'])
            if not budget_match:
                continue
        
        # Пол
        if 'gender' in filters:
            if filters['gender'] not in gender_tags:
                continue
        
        # Возраст
        if 'age' in filters:
            if filters['age'] not in age_tags:
                continue
        
        # Отношения
        if 'relationship' in filters:
            if filters['relationship'] not in relationship_tags:
                continue
        
        # Повод
        if 'occasion' in filters:
            if filters['occasion'] not in occasion_tags:
                continue
        
        # === ПАРСИМ ТЕГИ ПОДАРКА ===
        def get_tag_value(tags_str, tag_name):
            for part in tags_str.split(','):
                part = part.strip()
                if tag_name in part and ':' in part:
                    try:
                        return float(part.split(':')[1])
                    except:
                        pass
            return 0.0
        
        gift_practical = get_tag_value(value_tags, 'gift_practical')
        gift_emotional = get_tag_value(value_tags, 'gift_emotional')
        gift_experience = get_tag_value(value_tags, 'gift_experience')
        gift_daily_use = get_tag_value(value_tags, 'gift_daily_use')
        gift_aesthetic = get_tag_value(value_tags, 'gift_aesthetic')
        
        # === ЖЁСТКАЯ ФИЛЬТРАЦИЯ ПО ВЕЩЬ/ВПЕЧАТЛЕНИЕ ===
        user_experience = value_weights.get('gift_experience', 0.5)
        
        if user_experience == 0 and gift_experience > 0.7:
            continue
        
        if user_experience == 1 and gift_experience < 0.3:
            continue
        
        # === SCORING ===
        score = 0.0
        
        # 0. БЮДЖЕТ — умный расчёт баллов
        if 'budget' in filters and filters['budget']:
            user_max_budget = filters['budget'][-1]  # Последний = максимальный
            budget_score = calculate_budget_score(user_max_budget, budget_tags)
            score += budget_score
        
        # 1. Практичный vs Эмоциональный
        user_practical = value_weights.get('gift_practical', 0.5)
        user_emotional = value_weights.get('gift_emotional', 0.5)
        
        if user_practical == 1:
            score += gift_practical * 2.0
            score -= gift_emotional * 1.0
        elif user_emotional == 1:
            score += gift_emotional * 2.0
            score -= gift_practical * 0.5
        else:
            score += gift_practical * 0.5
            score += gift_emotional * 0.5
        
        # 2. Для ежедневного использования
        user_daily = value_weights.get('gift_daily_use', 0.5)
        
        if user_daily == 1:
            score += gift_daily_use * 1.5
            if gift_daily_use < 0.3:
                score -= 0.5
        elif user_daily == 0:
            if gift_daily_use > 0.7:
                score -= 0.3
        
        # 3. Эстетика
        user_aesthetic = value_weights.get('gift_aesthetic', 0.5)
        
        if user_aesthetic == 1:
            score += gift_aesthetic * 1.5
            if gift_aesthetic < 0.3:
                score -= 0.5
        
        # 4. INTERESTS — главный множитель!
        interest_bonus = 0.0
        interest_matches = 0
        
        for tag, user_weight in interest_weights.items():
            if user_weight > 0:
                tag_value = get_tag_value(interest_tags, tag)
                if tag_value > 0:
                    interest_bonus += tag_value * 3.0
                    interest_matches += 1
        
        score += interest_bonus
        
        if interest_matches >= 2:
            score += 1.0
        if interest_matches >= 3:
            score += 1.5
        
        results.append({
            'id': gift_id,
            'name': name,
            'price': price,
            'description': description,
            'score': score,
            'interest_matches': interest_matches
        })
    
    # Сортируем по score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results


def get_top_gifts(filters: dict, value_weights: dict, interest_weights: dict, limit: int = 5):
    """Возвращает топ-N подарков"""
    results = filter_and_score_gifts(filters, value_weights, interest_weights)
    return results[:limit]


# === ТЕСТ ===
if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТ: Бюджет 10к — товары 10-50к должны быть ВНИЗУ")
    print("=" * 60)
    
    # Товар с диапазоном 10к-50к
    test_tags = "budget_10000, budget_15000, budget_20000, budget_30000, budget_50000"
    
    print(f"\nТовар: {test_tags}")
    print()
    
    for budget in BUDGET_ORDER:
        score = calculate_budget_score(budget, test_tags)
        print(f"Юзер {budget}: {score:+.1f} баллов")
    
    print()
    print("=" * 60)
    print("ТЕСТ: Товар 2к-5к")
    print("=" * 60)
    
    test_tags2 = "budget_2000, budget_5000"
    print(f"\nТовар: {test_tags2}")
    print()
    
    for budget in BUDGET_ORDER:
        score = calculate_budget_score(budget, test_tags2)
        print(f"Юзер {budget}: {score:+.1f} баллов")