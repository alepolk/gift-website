from flask import Flask, render_template, request, jsonify, session
from scoring import get_top_gifts
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Вопросы (те же что в боте)
QUESTIONS = [
    {
        "id": 1,
        "text": "Какой у вас бюджет на подарок?",
        "icon": "💰",
        "options": [
            {"text": "До 2,000₽", "value": "budget_2000"},
            {"text": "До 5,000₽", "value": "budget_5000"},
            {"text": "До 10,000₽", "value": "budget_10000"},
            {"text": "До 15,000₽", "value": "budget_15000"},
            {"text": "До 20,000₽", "value": "budget_20000"},
            {"text": "До 30,000₽", "value": "budget_30000"},
            {"text": "До 50,000₽", "value": "budget_50000"},
            {"text": "До 100,000₽", "value": "budget_100000"},
        ],
        "type": "primary",
        "tag": "budget"
    },
    {
        "id": 2,
        "text": "Кому выбираете подарок?",
        "icon": "👤",
        "options": [
            {"text": "Мужчине", "value": "gender_male"},
            {"text": "Женщине", "value": "gender_female"},
        ],
        "type": "primary",
        "tag": "gender"
    },
    {
        "id": 3,
        "text": "Сколько лет получателю?",
        "icon": "🎂",
        "options": [
            {"text": "13-15 лет", "value": "age_13_15"},
            {"text": "16-19 лет", "value": "age_16_19"},
            {"text": "20-25 лет", "value": "age_20_25"},
            {"text": "26-35 лет", "value": "age_26_35"},
            {"text": "36-50 лет", "value": "age_36_50"},
            {"text": "51-65 лет", "value": "age_51_65"},
            {"text": "65+ лет", "value": "age_65plus"},
        ],
        "type": "primary",
        "tag": "age"
    },
    {
        "id": 4,
        "text": "Кем вам приходится этот человек?",
        "icon": "👨‍👩‍👧",
        "options": [
            {"text": "Муж/Жена", "value": "relationship_spouse"},
            {"text": "Партнёр", "value": "relationship_partner"},
            {"text": "Родитель", "value": "relationship_parent"},
            {"text": "Бабушка/Дедушка", "value": "relationship_grandparent"},
            {"text": "Ребёнок", "value": "relationship_child"},
            {"text": "Брат/Сестра", "value": "relationship_sibling"},
            {"text": "Друг/Подруга", "value": "relationship_friend"},
            {"text": "Коллега/Начальник", "value": "relationship_colleague"},
        ],
        "type": "primary",
        "tag": "relationship"
    },
    {
        "id": 5,
        "text": "По какому поводу дарите?",
        "icon": "🎉",
        "options": [
            {"text": "День рождения", "value": "occasion_birthday"},
            {"text": "Новый год", "value": "occasion_newyear"},
            {"text": "23 февраля / 8 марта", "value": "occasion_8march_23feb"},
            {"text": "День Валентина", "value": "occasion_valentine"},
            {"text": "Годовщина/Свадьба", "value": "occasion_wedding"},
            {"text": "Без повода", "value": "occasion_noreason"},
        ],
        "type": "primary",
        "tag": "occasion"
    },
    {
        "id": 6,
        "text": "Что лучше подарить?",
        "icon": "🎁",
        "options": [
            {"text": "Вещь (материальный подарок)", "value": "0"},
            {"text": "Впечатление (сертификат, билеты)", "value": "1"},
            {"text": "Не знаю", "value": "0.5"},
        ],
        "type": "value",
        "tag": "gift_experience"
    },
    {
        "id": 7,
        "text": "Какой подарок предпочтительнее?",
        "icon": "🎯",
        "options": [
            {"text": "Практичный (полезный в быту)", "value": "practical"},
            {"text": "Эмоциональный (для радости)", "value": "emotional"},
            {"text": "Не знаю", "value": "neutral"},
        ],
        "type": "value",
        "tag": "practical_emotional"
    },
    {
        "id": 8,
        "text": "Подарок для ежедневного использования?",
        "icon": "📅",
        "options": [
            {"text": "Да, на каждый день", "value": "1"},
            {"text": "Нет, пусть будет особенным", "value": "0"},
            {"text": "Не важно", "value": "0.5"},
        ],
        "type": "value",
        "tag": "gift_daily_use"
    },
    {
        "id": 9,
        "text": "Насколько важна красота подарка?",
        "icon": "✨",
        "options": [
            {"text": "Очень важна", "value": "1"},
            {"text": "Не очень важна", "value": "0"},
            {"text": "Не знаю", "value": "0.5"},
        ],
        "type": "value",
        "tag": "gift_aesthetic"
    },
]

INTERESTS_MALE = [
    {"text": "📱 Техника и гаджеты", "value": "interest_tech"},
    {"text": "⚽ Спорт и фитнес", "value": "interest_sports"},
    {"text": "🚗 Авто и мото", "value": "interest_car"},
    {"text": "🏕️ Природа и туризм", "value": "interest_nature"},
    {"text": "🌻 Дача и сад", "value": "interest_gardening"},
    {"text": "🎮 Игры", "value": "interest_gaming"},
    {"text": "✈️ Путешествия", "value": "interest_travel"},
    {"text": "🎵 Музыка", "value": "interest_music"},
    {"text": "📸 Фото и видео", "value": "interest_photography"},
    {"text": "🍳 Кулинария", "value": "interest_cooking"},
    {"text": "📚 Книги и чтение", "value": "interest_reading"},
    {"text": "☕ Кофе и чай", "value": "interest_coffee_tea"},
    {"text": "💼 Бизнес и карьера", "value": "interest_business"},
]

INTERESTS_FEMALE = [
    {"text": "💄 Красота и уход", "value": "interest_beauty"},
    {"text": "👗 Мода и стиль", "value": "interest_fashion"},
    {"text": "💎 Украшения и аксессуары", "value": "interest_accessories"},
    {"text": "🧘 Спорт и фитнес", "value": "interest_sports"},
    {"text": "🍳 Кулинария", "value": "interest_cooking"},
    {"text": "🏠 Дом и уют", "value": "interest_home"},
    {"text": "✈️ Путешествия", "value": "interest_travel"},
    {"text": "📚 Книги и чтение", "value": "interest_reading"},
    {"text": "🎨 Творчество", "value": "interest_creative"},
    {"text": "🌸 Растения и сад", "value": "interest_gardening"},
    {"text": "🎭 Кино и театр", "value": "interest_culture"},
    {"text": "📸 Фото и видео", "value": "interest_photography"},
    {"text": "☕ Кофе и чай", "value": "interest_coffee_tea"},
]

INTERESTS_ELDERLY = [
    {"text": "🌻 Дача и сад", "value": "interest_gardening"},
    {"text": "💪 Здоровье и комфорт", "value": "interest_health"},
    {"text": "📚 Книги и чтение", "value": "interest_reading"},
    {"text": "🎨 Рукоделие", "value": "interest_creative"},
    {"text": "🍳 Кулинария", "value": "interest_cooking"},
    {"text": "🎭 Кино и театр", "value": "interest_culture"},
    {"text": "🏠 Дом и уют", "value": "interest_home"},
    {"text": "☕ Кофе и чай", "value": "interest_coffee_tea"},
]


def get_budget_tags(selected_budget):
    all_budgets = ["budget_2000", "budget_5000", "budget_10000", "budget_15000",
                   "budget_20000", "budget_30000", "budget_50000", "budget_100000"]
    if selected_budget in all_budgets:
        index = all_budgets.index(selected_budget)
        return all_budgets[:index + 1]
    return all_budgets


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/quiz')
def quiz():
    session['answers'] = {}
    return render_template('quiz.html', questions=QUESTIONS)


@app.route('/api/interests')
def get_interests():
    gender = request.args.get('gender', 'gender_male')
    age = request.args.get('age', 'age_26_35')
    
    if age == 'age_65plus':
        return jsonify(INTERESTS_ELDERLY)
    elif gender == 'gender_female':
        return jsonify(INTERESTS_FEMALE)
    else:
        return jsonify(INTERESTS_MALE)


@app.route('/api/results', methods=['POST'])
def get_results():
    data = request.json
    
    # Формируем фильтры
    filters = {}
    value_weights = {
        'gift_practical': 0.5,
        'gift_emotional': 0.5,
        'gift_experience': 0.5,
        'gift_daily_use': 0.5,
        'gift_aesthetic': 0.5,
    }
    interest_weights = {}
    
    # Обрабатываем ответы
    for answer in data.get('answers', []):
        tag = answer.get('tag')
        value = answer.get('value')
        
        if tag == 'budget':
            filters['budget'] = get_budget_tags(value)
        elif tag in ['gender', 'age', 'relationship', 'occasion']:
            filters[tag] = value
        elif tag == 'gift_experience':
            value_weights['gift_experience'] = float(value)
        elif tag == 'practical_emotional':
            if value == 'practical':
                value_weights['gift_practical'] = 1.0
                value_weights['gift_emotional'] = 0.0
            elif value == 'emotional':
                value_weights['gift_practical'] = 0.0
                value_weights['gift_emotional'] = 1.0
        elif tag == 'gift_daily_use':
            value_weights['gift_daily_use'] = float(value)
        elif tag == 'gift_aesthetic':
            value_weights['gift_aesthetic'] = float(value)
    
    # Обрабатываем интересы
    for interest in data.get('interests', []):
        interest_weights[interest] = 1.0
    
    # Получаем результаты
    gifts = get_top_gifts(filters, value_weights, interest_weights, limit=50)
    
    return jsonify(gifts)


if __name__ == '__main__':
    app.run(debug=True, port=5000)