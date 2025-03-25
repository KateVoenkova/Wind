import re
from pymorphy2 import MorphAnalyzer

# Инициализация морфологического анализатора
morph = MorphAnalyzer()


def normalize_name(name):
    """
    Приводит имя к начальной форме (именительный падеж).
    """
    parts = name.split()
    normalized_parts = []
    for part in parts:
        parsed = morph.parse(part)[0]
        normalized_parts.append(parsed.normal_form)
    return ' '.join(normalized_parts)


def extract_all_names(text):
    # Регулярное выражение для поиска всех имён (1-3 слова с заглавной буквы)
    name_pattern = re.compile(r'\b([А-Я][а-я]+)(?:\s+([А-Я][а-я]+))?(?:\s+([А-Я][а-я]+))?\b')
    matches = name_pattern.findall(text)

    # Регулярное выражение для поиска фамилий и обращений (например, "граф Безухов")
    surname_pattern = re.compile(r'\b(граф|князь|генерал)?\s*([А-Я][а-я]+)\b')
    surname_matches = surname_pattern.findall(text)

    # Собираем все имена
    all_names = []
    for match in matches:
        # Соединяем слова в имя (убираем пустые части)
        name = ' '.join([part for part in match if part])
        all_names.append(name)

    # Собираем фамилии и обращения
    for match in surname_matches:
        # Соединяем обращение и фамилию (если есть)
        surname = ' '.join([part for part in match if part])
        all_names.append(surname)

    # Фильтрация: оставляем только имена, которые pymorphy2 считает именем собственным
    filtered_names = []
    for name in all_names:
        # Разбиваем имя на части и проверяем каждую часть
        parts = name.split()
        is_valid = True
        for part in parts:
            parsed = morph.parse(part)[0]
            if 'Name' not in parsed.tag and 'Surn' not in parsed.tag:  # Проверяем, является ли часть именем или фамилией
                is_valid = False
                break
        if is_valid:
            filtered_names.append(name)

    # Нормализация имён (приведение к начальной форме)
    normalized_names = [normalize_name(name) for name in filtered_names]

    # Удаление дубликатов
    unique_names = list(set(normalized_names))
    return unique_names


def get_names_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()

    names = extract_all_names(text)
    return names