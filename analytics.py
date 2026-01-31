import sqlite3
from datetime import datetime
import json

DB_PATH = "analytics.db"


def init_db():
    """Создаёт таблицы аналитики"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Сессии подбора
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed INTEGER DEFAULT 0
        )
    ''')
    
    # Ответы на вопросы (профиль пользователя)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            gender TEXT,
            age TEXT,
            relationship TEXT,
            occasion TEXT,
            budget TEXT,
            experience REAL,
            practical_emotional TEXT,
            daily_use REAL,
            aesthetic REAL,
            interests TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    ''')
    
    # Оценки подарков
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            gift_id INTEGER NOT NULL,
            gift_name TEXT,
            rating INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    ''')
    
    # События воронки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            event_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База аналитики создана")


def create_session(source: str, user_id: str = None) -> int:
    """Создаёт новую сессию, возвращает session_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO sessions (source, user_id) VALUES (?, ?)',
        (source, user_id)
    )
    session_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return session_id


def save_answers(session_id: int, filters: dict, value_weights: dict, interests: list):
    """Сохраняет ответы пользователя (профиль)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO answers (
            session_id, gender, age, relationship, occasion, budget,
            experience, practical_emotional, daily_use, aesthetic, interests
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session_id,
        filters.get('gender'),
        filters.get('age'),
        filters.get('relationship'),
        filters.get('occasion'),
        json.dumps(filters.get('budget', [])),
        value_weights.get('gift_experience'),
        'practical' if value_weights.get('gift_practical') == 1 else ('emotional' if value_weights.get('gift_emotional') == 1 else 'neutral'),
        value_weights.get('gift_daily_use'),
        value_weights.get('gift_aesthetic'),
        json.dumps(interests)
    ))
    
    conn.commit()
    conn.close()


def save_rating(session_id: int, gift_id: int, gift_name: str, rating: int):
    """Сохраняет оценку подарка (+1 лайк, -1 дизлайк)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO ratings (session_id, gift_id, gift_name, rating) VALUES (?, ?, ?, ?)',
        (session_id, gift_id, gift_name, rating)
    )
    
    conn.commit()
    conn.close()


def save_event(session_id: int, event_type: str, event_data: dict = None):
    """Сохраняет событие воронки"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO events (session_id, event_type, event_data) VALUES (?, ?, ?)',
        (session_id, event_type, json.dumps(event_data) if event_data else None)
    )
    
    conn.commit()
    conn.close()


def complete_session(session_id: int):
    """Помечает сессию как завершённую"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        'UPDATE sessions SET completed = 1 WHERE id = ?',
        (session_id,)
    )
    
    conn.commit()
    conn.close()


def get_collaborative_score(gift_id: int, filters: dict) -> float:
    """
    Рассчитывает бонус на основе лайков похожих пользователей.
    
    Ищет сессии с похожим профилем и смотрит их оценки этого подарка.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Находим похожие сессии (совпадение по gender, age, occasion)
    cursor.execute('''
        SELECT a.session_id 
        FROM answers a
        WHERE a.gender = ? 
          AND a.age = ?
          AND a.occasion = ?
    ''', (
        filters.get('gender'),
        filters.get('age'),
        filters.get('occasion')
    ))
    
    similar_sessions = [row[0] for row in cursor.fetchall()]
    
    if not similar_sessions:
        conn.close()
        return 0.0
    
    # Считаем лайки и дизлайки этого подарка
    placeholders = ','.join(['?' for _ in similar_sessions])
    cursor.execute(f'''
        SELECT 
            SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as likes,
            SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) as dislikes
        FROM ratings
        WHERE session_id IN ({placeholders}) AND gift_id = ?
    ''', similar_sessions + [gift_id])
    
    row = cursor.fetchone()
    conn.close()
    
    likes = row[0] or 0
    dislikes = row[1] or 0
    
    total = likes + dislikes
    if total == 0:
        return 0.0
    
    # Рассчитываем скор от -1 до +1, умножаем на вес
    score = (likes - dislikes) / total
    
    # Учитываем количество оценок (больше оценок = больше доверия)
    confidence = min(total / 10, 1.0)  # Максимум при 10+ оценках
    
    return score * confidence * 3.0  # До ±3 баллов


# ============== СТАТИСТИКА ==============

def get_funnel_stats():
    """Статистика воронки"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM sessions')
    total_sessions = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM sessions WHERE completed = 1')
    completed_sessions = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT session_id) FROM ratings')
    sessions_with_ratings = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'completion_rate': round(completed_sessions / total_sessions * 100, 1) if total_sessions > 0 else 0,
        'sessions_with_ratings': sessions_with_ratings
    }


def get_answer_distribution():
    """Распределение ответов по вопросам"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {}
    
    # Пол
    cursor.execute('SELECT gender, COUNT(*) FROM answers GROUP BY gender')
    stats['gender'] = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Возраст
    cursor.execute('SELECT age, COUNT(*) FROM answers GROUP BY age')
    stats['age'] = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Отношения
    cursor.execute('SELECT relationship, COUNT(*) FROM answers GROUP BY relationship')
    stats['relationship'] = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Повод
    cursor.execute('SELECT occasion, COUNT(*) FROM answers GROUP BY occasion')
    stats['occasion'] = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    return stats


def get_gift_ratings():
    """Рейтинг подарков по лайкам"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            gift_id,
            gift_name,
            SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as likes,
            SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) as dislikes,
            COUNT(*) as total
        FROM ratings
        GROUP BY gift_id, gift_name
        ORDER BY likes - dislikes DESC
    ''')
    
    results = []
    for row in cursor.fetchall():
        results.append({
            'gift_id': row[0],
            'gift_name': row[1],
            'likes': row[2],
            'dislikes': row[3],
            'total': row[4],
            'score': row[2] - row[3]
        })
    
    conn.close()
    return results


def print_stats():
    """Выводит статистику в консоль"""
    print("\n" + "=" * 60)
    print("📊 СТАТИСТИКА АНАЛИТИКИ")
    print("=" * 60)
    
    funnel = get_funnel_stats()
    print(f"\n🔄 ВОРОНКА:")
    print(f"   Всего сессий: {funnel['total_sessions']}")
    print(f"   Завершено: {funnel['completed_sessions']} ({funnel['completion_rate']}%)")
    print(f"   С оценками: {funnel['sessions_with_ratings']}")
    
    dist = get_answer_distribution()
    print(f"\n📋 РАСПРЕДЕЛЕНИЕ ОТВЕТОВ:")
    
    print(f"\n   Пол:")
    for k, v in dist.get('gender', {}).items():
        print(f"      {k}: {v}")
    
    print(f"\n   Возраст:")
    for k, v in dist.get('age', {}).items():
        print(f"      {k}: {v}")
    
    print(f"\n   Повод:")
    for k, v in dist.get('occasion', {}).items():
        print(f"      {k}: {v}")
    
    ratings = get_gift_ratings()
    print(f"\n🎁 ТОП ПОДАРКОВ ПО ЛАЙКАМ:")
    for i, gift in enumerate(ratings[:10], 1):
        print(f"   {i}. {gift['gift_name']}: +{gift['likes']} / -{gift['dislikes']} = {gift['score']}")
    
    if ratings:
        print(f"\n👎 ХУДШИЕ ПОДАРКИ:")
        for gift in ratings[-5:]:
            print(f"   • {gift['gift_name']}: +{gift['likes']} / -{gift['dislikes']} = {gift['score']}")


# Инициализация при импорте
init_db()


if __name__ == "__main__":
    print_stats()