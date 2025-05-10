from models import db, Character, CharacterRelationship
from collections import defaultdict
import re
import chardet
from typing import Dict, List, Tuple

class RelationshipFinder:
    def __init__(self, book_id: int, window_size: int = 100):
        self.book_id = book_id
        self.window_size = window_size
        self.characters = self._load_characters()

    def _load_characters(self) -> Dict[str, int]:
        characters = Character.query.filter_by(book_id=self.book_id).all()
        return {char.normalized_name: char.id for char in characters}

    def _find_mentions(self, text: str) -> List[Tuple[int, str]]:
        mentions = []
        words = re.findall(r'\b\w+\b', text.lower())
        for idx, word in enumerate(words):
            if word in self.characters:
                mentions.append((idx, word))
        return mentions

    def _count_relationships(self, mentions: List[Tuple[int, str]]) -> Dict[Tuple[int, int], int]:
        relationships = defaultdict(int)
        for i in range(len(mentions)):
            for j in range(i + 1, len(mentions)):
                pos_i, char_i = mentions[i]
                pos_j, char_j = mentions[j]
                if abs(pos_i - pos_j) <= self.window_size:
                    id1 = self.characters[char_i]
                    id2 = self.characters[char_j]
                    key = (min(id1, id2), max(id1, id2))
                    relationships[key] += 1
        return relationships

    def process_text(self, text: str):
        mentions = self._find_mentions(text)
        relationships = self._count_relationships(mentions)

        for (char1_id, char2_id), weight in relationships.items():
            if char1_id == char2_id:
                continue

            relationship = CharacterRelationship.query.filter_by(
                book_id=self.book_id,
                character1_id=char1_id,
                character2_id=char2_id
            ).first()

            if relationship:
                relationship.weight += weight
            else:
                relationship = CharacterRelationship(
                    character1_id=char1_id,
                    character2_id=char2_id,
                    book_id=self.book_id,
                    weight=weight
                )
                db.session.add(relationship)

        db.session.commit()

def find_relationships(book_id: int, file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'rb') as f:
            encoding = chardet.detect(f.read())['encoding']
        with open(file_path, 'r', encoding=encoding) as f:
            text = f.read()

    finder = RelationshipFinder(book_id)
    finder.process_text(text)