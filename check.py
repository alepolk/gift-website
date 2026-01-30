import sqlite3

conn = sqlite3.connect("gifts.db")
cursor = conn.cursor()

# Фильтры: парень, День Валентина
cursor.execute("SELECT id, name, gender_tags, occasion_tags FROM gifts")
rows = cursor.fetchall()
conn.close()

print("Подарки для парня на День Валентина:\n")

count = 0
for row in rows:
    gender = str(row[2] or '')
    occasion = str(row[3] or '')
    
    has_male = 'gender_male' in gender
    has_valentine = 'occasion_valentine' in occasion
    
    if has_male and has_valentine:
        count += 1
        if count <= 20:
            print(f"{row[0]}. {row[1]}")

print(f"\nВсего найдено: {count}")